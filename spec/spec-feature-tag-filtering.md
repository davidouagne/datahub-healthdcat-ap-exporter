# PRD — Durcir le filtrage par tag (`--tag`)

**Statut** : draft
**Date** : 2026-08-15
**Auteur** : David Ouagne

## Problem Statement

`dh-healthdcat` filtre déjà les DataProducts par tag : `--tag` existe sur
`export-file` et `push-hdh`, implémenté dans `src/dh_healthdcat/selection.py`.
Ce n'est pas une fonctionnalité manquante mais une implémentation v0 avec
trois faiblesses concrètes qui affectent tout utilisateur au-delà d'un petit
catalogue de test.

**1. Le filtrage est intégralement côté client, en O(N).**
`select_data_product_urns` (`selection.py:38-52`) appelle `discover_urns`
(`selection.py:10-13`), qui récupère **tous** les URNs de DataProducts du
catalogue via `get_urns_by_filter(entity_types=["dataProduct"])` sans aucun
filtre supplémentaire. Chaque candidat est ensuite testé par
`entity_has_any` (`selection.py:16-27`), qui appelle `ctx.get_entity(urn)` —
un aller-retour GMS par candidat, mémoïsé mais jamais évité — uniquement pour
lire son aspect `globalTags`. Sélectionner 3 DataProducts sur un catalogue de
2000 coûte aujourd'hui environ 2000 appels réseau au lieu d'une seule requête
de recherche filtrée.

**2. La sémantique combinatoire n'est ni symétrique ni documentée.**
Plusieurs valeurs `--tag` sont combinées en OU (`any(t.tag in wanted for t in
aspect.tags)`, `selection.py:26`) ; plusieurs `--domain` aussi. Mais `--tag`
et `--domain` entre eux sont combinés en ET (`selection.py:51`). Rien ne
permet d'exiger la présence de *tous* les tags d'une liste, ni d'exclure un
tag (par exemple : tout sauf `dcat:sample`).

**3. `selection.py` n'a aucune couverture de test**, alors qu'il conditionne
la sélection de chaque export (`export-file`) et de chaque envoi vers le
catalogue HDH (`push-hdh`) — une régression y est silencieuse jusqu'à ce
qu'un utilisateur constate qu'un DataProduct attendu manque à l'export.

Qui est affecté : tout utilisateur de `dh-healthdcat` sur un catalogue
DataHub de taille réelle (au-delà d'une poignée de DataProducts), en
particulier lors d'exports ciblés répétés (CI, exports périodiques par
domaine).

## Goals

- Le coût réseau d'une sélection par tag/domaine ne dépend plus du nombre
  total de DataProducts du catalogue, seulement du nombre de résultats
  (une requête de recherche filtrée, au lieu de N+1 appels).
- La sémantique de combinaison des filtres (ET/OU entre tags, exclusion) est
  explicite dans l'interface CLI et couverte par des tests, plutôt
  qu'implicite dans le code.
- `selection.py` passe d'une couverture de test nulle à une couverture des
  quatre sémantiques de filtrage (OU, ET, exclusion, combinaison
  domaine+tag), sans dépendre d'un réseau ou d'une instance DataHub réelle.

## Non-Goals

- **Filtrage au niveau Dataset** (au sein d'un DataProduct sélectionné) —
  la sélection reste au niveau DataProduct, cohérent avec le mapping actuel
  (`docs/mapping.md`, DataProduct → `dcat:Dataset`). Périmètre séparé.
- **Filtres sur les structured properties** (ex. `--health-category HRAD`) —
  capacité différente, pas demandée ici.
- **Validation d'existence des tags avant filtrage** (détecter qu'un
  `--tag` ne correspond à aucun tag existant plutôt qu'à un ensemble de
  résultats vide) — reportée en P1 : utile mais pas bloquante pour l'usage
  normal, et nécessite une résolution supplémentaire (lister les tags
  existants) hors du strict passage à l'échelle visé ici.
- **Refonte de la CLI `export-file`/`push-hdh`** — seules les options de
  filtrage évoluent, pas la structure des commandes.

## User Stories

**Exploitant du catalogue**
- En tant qu'exploitant du catalogue DataHub, je veux exporter uniquement les
  DataProducts d'un domaine donné sans que le temps d'export dépende de la
  taille totale du catalogue, afin de pouvoir lancer des exports ciblés
  fréquents sans latence croissante.
- En tant qu'exploitant, je veux exclure les DataProducts marqués d'un tag
  donné (ex. `dcat:sample`, `deprecated`) de mes exports, sans avoir à lister
  positivement tous les tags à inclure.

**Intégrateur HDH**
- En tant qu'intégrateur poussant des DataProducts vers le HDH, je veux
  pouvoir exiger la présence simultanée de plusieurs tags (ex.
  `healthdcat:ready` ET `domaine:soins`) pour restreindre `push-hdh` à un
  sous-ensemble précis, plutôt que la seule sémantique OU actuelle.

**Mainteneur du projet**
- En tant que mainteneur, je veux que `selection.py` soit testé comme le
  reste du pipeline (`reader/`, `mapping/`), afin qu'une régression de
  filtrage soit détectée par `uv run pytest` plutôt qu'en production.

## Requirements

### Must-Have (P0)

| ID | Exigence | Critère d'acceptation |
|----|----------|------------------------|
| REQ-001 | La sélection par `--tag`/`--domain` est évaluée côté serveur (une requête de recherche), pas par énumération + filtrage client | Given un catalogue de N DataProducts dont k matchent les filtres, When `select_data_product_urns` est appelé avec `--tag`, Then le nombre d'appels au client DataHub ne dépend pas de N (une requête de recherche renvoyant directement les k URNs, pas N appels `get_entity`) |
| REQ-002 | La construction du filtre réutilise `datahub.sdk.search_filters.FilterDsl` (`tag`, `domain`, `and_`, `or_`, `not_`) plutôt que des structures de filtre construites à la main | Given les mêmes entrées CLI, When le filtre est compilé, Then sa forme correspond à celle produite par `FilterDsl.and_/or_/not_/tag/domain` (vérifié : `F.tag([a,b])` → une règle multi-valeurs OU ; `F.and_(F.tag([a]), F.tag([b]))` → deux règles ET ; `F.not_(F.tag([x]))` → règle `negated: true`) |
| REQ-003 | La CLI expose une sémantique explicite : `--tag-mode any\|all` (défaut `any`, rétrocompatible avec le comportement actuel) et `--exclude-tag` (répétable) | Given `--tag A --tag B --tag-mode all`, When la sélection s'exécute, Then seuls les DataProducts portant A **et** B sont retenus. Given `--exclude-tag C`, When la sélection s'exécute, Then aucun DataProduct portant C n'est retenu, même s'il matche par ailleurs |
| REQ-004 | La construction du filtre (entrées CLI → structure de filtre) est une fonction pure, sans dépendance à `ReadContext`/réseau, testable isolément | Given des entrées CLI arbitraires (tags, domaines, mode, exclusions), When la fonction de construction est appelée, Then elle renvoie une structure de filtre déterministe sans effectuer d'appel réseau |
| REQ-005 | `selection.py` est couvert par des tests unitaires pour les quatre sémantiques : OU de tags, ET de tags, exclusion, combinaison domaine+tag | Given la suite `tests/unit/test_selection.py` (à créer), When `uv run pytest` s'exécute, Then les 4 sémantiques ci-dessus sont chacune vérifiées sans instance DataHub |

### Nice-to-Have (P1)

| ID | Exigence | Critère d'acceptation |
|----|----------|------------------------|
| REQ-101 | Un `--tag`/`--domain` qui ne correspond à aucun tag/domaine existant dans le catalogue produit un avertissement explicite, distinct d'un filtre valide sans résultat | Given `--tag urn:li:tag:aphp:acces` (typo pour `aphp:access`), When la sélection renvoie un ensemble vide, Then le message distingue « tag inexistant dans le catalogue » de « tag existant, aucun DataProduct associé » |

### Future Considerations (P2)

- `--glossary-term` comme axe de filtrage supplémentaire (le `FilterDsl`
  sous-jacent le supporte déjà — `glossary_term`).

## Success Metrics

**Leading indicators**
- Nombre d'appels au client DataHub pour une sélection filtrée : passe de
  O(N) (N = taille du catalogue) à O(1) requête de recherche. Mesuré par
  instrumentation/comptage d'appels dans les tests (double `FakeGraph`
  comptant ses invocations).
- Couverture de `selection.py` : de 0 test à couverture des 4 sémantiques
  listées en REQ-005.

**Lagging indicators**
- Absence de régression de sélection signalée après mise en production
  (aujourd'hui non mesurable : aucun test n'existe pour détecter une
  régression avant qu'un utilisateur la constate).

## Open Questions

Les deux questions ci-dessous étaient ouvertes à la rédaction de cette spec ;
tranchées le 2026-08-15 avant implémentation du lot P0, décisions reportées
dans le tableau des exigences et le README.

- ~~**Défaut de `--tag-mode`**~~ — **Tranché : `any`.** Préserve la
  rétrocompatibilité avec le comportement actuel (OU implicite) : aucun export
  existant ne change de résultat après mise à jour.
- ~~**Interaction `--urn` explicite + `--tag`**~~ — **Tranché : `--urn` est
  prioritaire, les filtres sont ignorés** (avec avertissement explicite s'ils
  sont fournis en même temps). C'est un changement de comportement assumé par
  rapport au v0, où `select_data_product_urns` appliquait quand même les
  filtres `--tag`/`--domain` à la liste explicite (`selection.py:47-52` avant
  implémentation du lot P0) — comportement qui n'était documenté nulle part.

## Timeline Considerations

Aucune échéance contractuelle. Les exigences P0 forment un lot cohérent
(la fonction pure de REQ-004 est un prérequis structurel à REQ-005) livrable
en un seul incrément. P1/P2 en suivi, sans dépendance bloquante sur le lot P0.
