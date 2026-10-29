# Écarts connus entre le HDH et HealthDCAT-AP/DPV

## Politique

Les fichiers `mapping/vocab/*.yml` marqués comme **vendus** (voir
`mapping/vocab/README.md`) sont des copies conformes des dictionnaires du
Catalogue HDH. Le HDH est responsable de sa propre conformité vis-à-vis de
l'écosystème européen (HealthDCAT-AP, DPV) ; ce dépôt ne corrige **jamais**
localement le contenu d'un fichier vendu, même quand un écart avéré avec la
spec officielle est constaté (voir `CONTEXT.md`, terme « Vocabulaire vendu » :
« en cas de divergence, le HDH fait foi »).

Ce fichier consolide les écarts constatés, pour signalement côté HDH et
resynchronisation quand ils seront corrigés en amont. Il ne remplace pas le
détail des tickets d'origine (liens ci-dessous), il en donne la vue
d'ensemble.

## Liste des écarts

| Fichier | Entrée | Écart | Vérifié contre | Statut |
|---|---|---|---|---|
| `PersonalData.yml` | `vocabulary_list` (73 entrées) | 71 entrées utilisent `https://w3id.org/dpv/dpv-pd#…` (alias historique, toujours redirigé par w3id.org), 2 (`Identifying`, `Death`) utilisent `https://w3id.org/dpv/pd#…` (namespace canonique actuel). Deux IRI distinctes pour le même vocabulaire, sans casser la résolution (les deux redirigent vers le même document). | DPV v2.3 (module `pd`, https://w3id.org/dpv/pd) — 2026-09-18 | Ouvert, non corrigé ici (« HDH fait foi ») — voir #85 |
| `PersonalData.yml` | `Death` (`https://w3id.org/dpv/pd#Death`) | Ne correspond à aucun terme documenté dans DPV (ni le module `pd`, ni le cœur DPV) — l'IRI ne désigne aucun concept réel. | DPV v2.3 (core + module `pd`) — 2026-09-18 | Ouvert, non corrigé ici (« HDH fait foi ») — voir #86 |
| `HealthCategories.yml` / `HealthTheme.yml` | Namespace des URIs | Résolvent vers `http://healthdataportal.eu/resource/authority/{healthcategories,health-theme}/…` (namespace SEMIC) faute de vocabulaire `healthCategory`/`healthTheme` canonique publié par l'EC à ce jour. Sources HDH portaient historiquement un hôte de dév en dur (`13.81.34.152:1101`). | Vocabulaire HealthDCAT-AP `healthCategory` — inexistant côté EC au 2026-08 | **Repointé localement** (seul écart de ce tableau corrigé ici, avant l'adoption de cette politique) — issue #6, à resynchroniser quand l'EC/HDH publiera le vocabulaire officiel |

`HealthHistory` (retiré par erreur du côté du registre `datahub-data-gov-registry`,
MR `!9`, alors que c'est un terme DPV-PD valide et actif) n'est **pas** un
écart HDH vs HealthDCAT-AP — c'est un écart entre le registre AP-HP et le
vocabulaire réel de l'exporteur, déjà signalé et clos sur
`datahub-data-gov-registry#25` (voir #85).

## Pertes à l'ingestion HDH

Le Catalogue HDH ne conserve pas le Turtle poussé (`POST /ingest/datasets`) : il le
charge dans un graphe temporaire, le relit dans son modèle (`FullDatasetSerializer`) puis
réécrit son propre RDF (`app/turtle/services.py`, `_full_dataset_from_turtle_string`).
Toute propriété sans champ dans ce modèle disparaît, sans erreur. Ces propriétés restent
valides en HealthDCAT-AP : l'exporteur continue de les émettre (export Turtle, ouverture
européenne #132), même règle que pour les vocabulaires vendus.

| Propriété émise | Sort côté HDH | Source HDH | Émise par |
|---|---|---|---|
| `dcat:landingPage` | Perdue : lue par le parseur, mais le modèle n'a pas de champ | `app/form/services/rdf_graph_parser.py` (`_parse_dataset_from_graph`) | #145 |
| `foaf:page` | Perdue : idem | idem | #145 |
| `dct:relation` (direct), `dct:isPartOf`, `dct:hasPart`, `dcat:inSeries` | Perdues : non lues | idem | non émises (ADR-0006) |
| `dcat:qualifiedRelation` | Conservée, mais la cible `dct:relation` est réémise comme `dcat:DataService` (`dct:title` et `dcat:endpointURL` = l'IRI cible) ; un rôle hors vocabulaire `RoleQualifiedRelation` (relations IANA) est libellé « NA » | `app/form/serializers/dataset.py` (`to_turtle`) | #146 (ADR-0006) |

Vérifié sur le clone `healthdatahub/catalogue-de-metadonnees` au commit `fc5149f`
(2026-06-19), le 2026-10-29.

## Historique

- 2026-09-18 (#85) : audit initial de `PersonalData.yml` contre DPV v2.3,
  suite à `datahub-data-gov-registry#25`.
- 2026-09-18 (#86) : décision initiale de retirer `Death` localement (PR #89),
  **revenue en arrière** — la politique retenue est de rester conforme au
  contenu du HDH tel qu'il est vendu, et de consolider les écarts ici plutôt
  que de les corriger fichier par fichier.
- 2026-10-29 (#146, #147) : pertes à l'ingestion HDH, constatées en préparant
  ADR-0006.

## Ajouter un écart

1. Vérifier l'entrée contre la spec DPV/HealthDCAT-AP en vigueur (citer la
   version et la date).
2. Ajouter une ligne au tableau ci-dessus, sans modifier le fichier vendu.
3. Ouvrir un ticket de signalement (celui-ci ou un nouveau) référencé côté
   HDH quand un canal existe.
