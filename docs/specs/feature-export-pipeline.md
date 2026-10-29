# Spec — Pipeline d'export unifié et état de poussée durable

**Statut** : implémenté. Les références `fichier:ligne` datent de la rédaction.
**Date** : 2026-08-16
**Auteur** : David Ouagne

## Problem Statement

1. **Une poussée interrompue duplique les jeux dans le catalogue HDH.**
   `push-hdh` crée les datasets un par un mais n'écrit `state.json` qu'après la
   boucle entière. Une interruption (Ctrl-C, exception inattendue, coupure
   réseau) perd tous les ids déjà attribués ; la reprise recrée les mêmes jeux.
   C'est exactement ce que le fichier d'état existe pour empêcher.
2. **Les deux commandes traitent différemment un même DataProduct invalide,
   sans que rien ne le documente ni ne le garantisse.** `export-file`
   conditionne l'exclusion à `--strict` ; `push-hdh` n'a pas d'option `--strict`
   et exclut toujours. La différence est réelle et voulue, mais elle est
   aujourd'hui un accident de deux boucles écrites à la main, plutôt qu'une
   décision explicite.
3. **Une régression de la logique d'exclusion est silencieuse.**
   L'orchestration n'a aucun test, alors que c'est elle qui décide quel jeu
   sort de l'export ou de la poussée. Le dernier correctif en date (exclure un
   DataProduct invalide plutôt qu'échouer tout l'export) y a été appliqué sans
   qu'un test ne puisse le protéger d'une régression future.

Qui est affecté : tout exploitant lançant `export-file` sur un catalogue
contenant au moins un DataProduct invalide (module déjà partiellement couvert
par le correctif récent, mais pas par un test), et tout intégrateur lançant
`push-hdh` sur un lot suffisamment grand pour risquer une interruption
avant la fin.

## Solution

- Un module unique porte le pipeline (lecture → mapping → rapport d'issues →
  validation → décision), avec une seule interface franchie par les deux
  commandes **et** par les tests.
- `cli.py` ne garde que la présentation : outcome → couleur, compteur, code de
  sortie.
- L'état de poussée devient durable : il persiste après chaque succès, en
  écriture atomique. Une poussée interrompue reprend sans duplication.
- La différence de politique entre `export-file` et `push-hdh` devient un
  paramètre explicite du module, plutôt qu'un écart entre deux copies.

## User Stories

**Exploitant du catalogue (export-file)**

1. En tant qu'exploitant, je veux qu'un DataProduct invalide soit exclu sans
   faire échouer tout l'export, afin de récupérer les jeux valides du même lot.
2. En tant qu'exploitant, je veux voir en fin d'export combien de jeux ont été
   écrits et combien exclus, afin d'évaluer la qualité du catalogue sans relire
   tout le journal.
3. En tant qu'exploitant, je veux distinguer un DataProduct illisible (sans
   nom, DataProduct invalide côté DataHub) d'un DataProduct lisible mais non
   conforme SHACL, afin de savoir où porter la correction.
4. En tant qu'exploitant, je veux forcer un export exploratoire avec
   `--no-strict` tout en conservant le rapport d'issues, afin d'inspecter un
   catalogue en cours de peuplement sans qu'il bloque l'export.
5. En tant qu'exploitant, je veux le même diagnostic d'exclusion quel que soit
   le format de sortie choisi (`--format`), afin que le comportement reste
   prévisible indépendamment du format.
6. En tant qu'exploitant utilisant `--split-per-dataset`, je veux qu'aucun
   fichier ne soit écrit pour un jeu exclu, afin que le dossier de sortie ne
   contienne que des jeux réellement valides.
7. En tant qu'exploitant, je veux qu'un DataProduct valide ne soit jamais
   affecté par l'invalidité d'un autre DataProduct du même lot.

**Intégrateur HDH (push-hdh)**

8. En tant qu'intégrateur, je veux interrompre une poussée longue et la
   reprendre plus tard sans créer de doublons dans le catalogue HDH, afin de
   pouvoir pousser de gros lots sans crainte d'une coupure.
9. En tant qu'intégrateur, je veux qu'un jeu invalide ne soit jamais envoyé au
   HDH, même par inadvertance, afin de ne jamais publier de données non
   conformes.
10. En tant qu'intégrateur, je veux savoir pour chaque jeu s'il a été créé ou
    mis à jour, afin de suivre l'évolution du catalogue HDH au fil des
    poussées.
11. En tant qu'intégrateur, je veux voir en `--dry-run` exactement ce qui
    serait créé vs mis à jour, sans effectuer le moindre appel réseau
    d'écriture, afin de valider une poussée avant de l'exécuter pour de vrai.
12. En tant qu'intégrateur, je veux que `state.json` ne soit jamais corrompu,
    même en cas d'interruption pendant son écriture, afin de ne jamais perdre
    la correspondance URN → id HDH déjà connue.
13. En tant qu'intégrateur, je veux qu'un échec réseau sur un jeu n'empêche
    pas les jeux suivants d'être poussés, afin qu'une erreur isolée ne bloque
    pas tout le lot.
14. En tant qu'intégrateur, je veux un code de sortie non nul dès qu'au moins
    un jeu a échoué, afin qu'une CI puisse détecter l'échec sans parser le
    journal.
15. En tant qu'intégrateur, je veux que relancer `push-hdh` sur un lot déjà
    poussé mette à jour les jeux existants plutôt que d'en créer des
    doublons, afin que la commande reste idempotente à chaque relance.

**Mainteneur du projet**

16. En tant que mainteneur, je veux tester l'orchestration hors ligne, sans
    instance DataHub ni HDH, afin que `uv run pytest` détecte une régression
    avant un utilisateur.
17. En tant que mainteneur, je veux un test de non-régression pour le
    comportement « un DataProduct invalide est exclu, pas le lot entier »,
    afin que ce correctif récent reste garanti dans le temps.
18. En tant que mainteneur, je veux vérifier la durabilité de l'état de
    poussée sans avoir à simuler un vrai crash de processus, afin que ce
    comportement soit testable en quelques lignes.
19. En tant que mainteneur, je veux changer la politique d'exclusion
    (strict/non-strict) à un seul endroit, afin qu'`export-file` et
    `push-hdh` ne puissent plus diverger silencieusement.
20. En tant que mainteneur, je veux des tests qui décrivent des outcomes
    observables plutôt que la sortie terminal capturée, afin qu'ils survivent
    à un refactor interne du pipeline.

**Agent / CI**

21. En tant qu'agent lisant le résultat d'un export, je veux que les décisions
    du pipeline soient exposées comme des données typées plutôt que comme du
    texte destiné à un terminal, afin de pouvoir les consommer sans parser de
    la sortie colorée.
22. En tant que mainteneur ou agent modifiant le comportement d'export, je
    veux une seule interface à comprendre, afin de ne pas avoir à maintenir
    deux implémentations du même pipeline en parallèle.

## Implementation Decisions

- **Un module de pipeline** dont l'interface produit une séquence d'*outcomes*
  typés, un par DataProduct sélectionné, plutôt que d'écrire directement sur
  le terminal. Les outcomes distinguent trois cas : jeu préparé (pivot +
  graphe RDF, prêt à être écrit ou poussé), jeu illisible (le DataProduct n'a
  pas de nom exploitable côté DataHub — DataProduct invalide ou introuvable),
  jeu rejeté (erreurs de pivot et/ou non-conformité SHACL, avec le rapport
  détaillé joint à l'outcome). Les deux commandes consomment cette même
  séquence ; c'est elle qui devient l'unique seam testé.
- **La politique d'exclusion est un paramètre du module, pas une divergence
  entre deux boucles.** `export-file` la règle via `--strict/--no-strict`,
  inchangé côté CLI. `push-hdh` fixe la politique à « strict » et n'expose
  **pas** de `--no-strict` : ne jamais envoyer de données invalides au HDH est
  une propriété de sûreté déjà affirmée par le module de validation SHACL
  existant, pas une préférence configurable. La différence de comportement
  entre les deux commandes devient ainsi un choix explicite et visible à un
  seul endroit, plutôt qu'un écart accidentel entre deux implémentations.
- **La poussée vers le HDH (créer ou mettre à jour, puis enregistrer l'id)
  fait partie du pipeline**, pas de la CLI : c'est cette séquence précise qui
  porte le risque de duplication en cas d'interruption, donc elle doit être
  franchissable par un test, au même titre que la lecture et la validation.
- **Le client HDH devient un vrai seam** par l'ajout d'un adapter en mémoire
  utilisé par les tests, en plus de l'adapter réseau existant utilisé en
  production. Deux adapters justifient le seam ; un seul n'aurait été que de
  l'indirection sans bénéfice de test.
- **L'état de poussée (correspondance URN DataHub → id HDH) devient un module
  profond** : il possède le chemin du fichier et la politique de persistance,
  et non plus seulement la structure de données. Son interface se réduit à
  trois opérations : ouvrir l'état existant, lire l'id HDH connu pour un URN,
  enregistrer un id pour un URN. Enregistrer un id persiste immédiatement sur
  disque — le pipeline ne décide plus quand sauvegarder, il constate que
  chaque succès est déjà écrit.
- **L'écriture de l'état est atomique** (fichier temporaire écrit puis
  substitué à l'ancien), afin qu'une interruption pendant l'écriture ne
  laisse jamais un fichier d'état tronqué ou invalide en JSON.
- **La fonction d'état actuellement inutilisée (suppression d'une entrée) est
  retirée de l'interface** : elle n'a aujourd'hui aucun appelant dans le
  pipeline ni dans la CLI.
- **`cli.py` ne prend plus aucune décision d'inclusion/exclusion.** Il
  traduit chaque outcome du pipeline en couleur de sortie, en compteur agrégé
  et en code de sortie du processus. Les codes de sortie actuels sont
  conservés (2 = erreur d'usage sur la sélection, 1 = échec de traitement
  d'au moins un jeu).
- **Aucun changement du modèle pivot, du mapping RDF/HealthDCAT-AP, ni de la
  sélection des DataProducts** (`selection.py`, déjà spécifiée séparément).
  Ce lot ne touche que l'orchestration entre sélection et écriture/poussée.

## Testing Decisions

- **Ce qu'est un bon test ici** : il traverse l'interface du module de
  pipeline (et, pour la poussée, l'interface du client HDH) et affirme des
  outcomes observables — jamais un état interne du module, jamais la sortie
  terminal capturée. Un test qui doit changer parce que l'implémentation
  interne a changé, sans que le comportement observable ait changé, teste au
  mauvais niveau.
- **Prior art à suivre dans ce dépôt** :
  - `tests/unit/test_selection.py` — un double `FakeGraph` qui compte ses
    appels, et une fonction pure testée exhaustivement à côté d'un test
    d'intégration plus léger ; c'est le modèle le plus proche de ce que ce
    lot doit produire pour le pipeline.
  - `tests/unit/test_reader_dataproduct.py` — pilotage du reader via une
    fixture `build_context()` entièrement hors ligne, avec des cas construits
    à la main (propriété non déclarée, absence de profil).
  - `tests/unit/test_mapping_dataset.py` — modèle pivot construit à la main,
    assertion de conformité SHACL du graphe produit.
- **Tests à écrire** :
  - Le pipeline piloté par le double DataHub existant, affirmant la séquence
    d'outcomes (préparé / illisible / rejeté) pour un lot mixte.
  - La poussée pilotée par l'adapter HDH en mémoire, affirmant la distinction
    création vs mise à jour et l'enregistrement de l'id qui en résulte.
  - La durabilité de l'état de poussée via un répertoire temporaire : chaque
    enregistrement persiste immédiatement (rouvrir l'état après chaque étape
    et vérifier qu'il contient déjà ce qui vient d'être poussé, sans attendre
    la fin du lot).
  - Un test de non-régression explicite : dans une sélection de plusieurs
    DataProducts dont un seul est invalide, les autres sont bien exportés
    (comportement du correctif récent, aujourd'hui non protégé par un test).
- **La fixture DataHub doit être étendue.** Elle ne contient aujourd'hui qu'un
  seul DataProduct, entièrement valide. Il faut y ajouter au moins un
  DataProduct illisible (sans nom exploitable) et un DataProduct lisible mais
  non conforme SHACL, pour pouvoir exercer les trois outcomes du pipeline.
  C'est un vrai poste de travail de ce lot, pas un ajustement mineur.

## Out of Scope

- Les autres candidats identifiés lors de la revue d'architecture de ce
  dépôt : chargement unique des shapes SHACL (actuellement reparsées à
  chaque validation), regroupement des paramètres répétés dans le reader, et
  le sort du module de fusion en catalogue actuellement sans appelant.
- Le filtrage au niveau Dataset et les filtres sur structured properties —
  déjà explicitement hors périmètre dans `spec-feature-tag-filtering.md`.
- L'écriture en retour de l'id HDH dans DataHub via une structured property
  (`--write-back`), déjà notée comme alternative non retenue par le module
  d'état actuel.
- Toute modification du modèle pivot, du mapping RDF ou des shapes SHACL du
  HDH.
- Toute modification du workflow CI.

## Further Notes

- Ce dépôt n'a ni `CONTEXT.md` ni journal de décisions d'architecture : le
  vocabulaire métier utilisé ici est repris directement du code (DataProduct,
  modèle pivot, distribution, échantillon, issue). Aucune décision
  d'architecture enregistrée n'est remise en cause par ce lot.
- Le vocabulaire de conception (**module**, **interface**, **seam**,
  **adapter**, **leverage**, **locality**) est conservé en anglais, à
  l'identique de la revue d'architecture dont ce lot est issu.
- Voir `feature-tag-filtering.md` pour la sélection des
  DataProducts en amont de ce pipeline (non modifiée par ce lot).
