# Écarts connus entre le vocabulaire vendu HDH et HealthDCAT-AP/DPV

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

## Historique

- 2026-09-18 (#85) : audit initial de `PersonalData.yml` contre DPV v2.3,
  suite à `datahub-data-gov-registry#25`.
- 2026-09-18 (#86) : décision initiale de retirer `Death` localement (PR #89),
  **revenue en arrière** — la politique retenue est de rester conforme au
  contenu du HDH tel qu'il est vendu, et de consolider les écarts ici plutôt
  que de les corriger fichier par fichier.

## Ajouter un écart

1. Vérifier l'entrée contre la spec DPV/HealthDCAT-AP en vigueur (citer la
   version et la date).
2. Ajouter une ligne au tableau ci-dessus, sans modifier le fichier vendu.
3. Ouvrir un ticket de signalement (celui-ci ou un nouveau) référencé côté
   HDH quand un canal existe.
