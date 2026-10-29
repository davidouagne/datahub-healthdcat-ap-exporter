# Contribuer à datahub-healthdcat-ap-exporter

## Mise en place de l'environnement

```bash
uv sync
```

Cela crée `.venv/` et installe le projet en mode éditable avec le groupe de
dépendances `dev` (PEP 735). Sans `uv`, un `venv` standard fonctionne aussi
(pip ≥ 25.1 pour `--group`) :

```bash
python -m venv .venv
.venv/Scripts/activate  # ou source .venv/bin/activate sous Linux/macOS
pip install -e . --group dev
```

## Lancer les tests

```bash
uv run pytest
```

Aucun test ne nécessite d'instance [DataHub](https://datahubproject.io/) ou [Catalogue de métadonnées de la Plateforme des Données de Santé](https://catalogue-metadonnees.health-data-hub.fr/) réelle : le `reader` est
testé contre un double (`tests/fixtures/fake_datahub.py`), le `mapping` et la
validation SHACL contre des graphes construits à la main. Toute contribution
touchant à la lecture DataHub ou au mapping RDF doit rester testable hors
ligne de la même façon. Seul le contrôle Docker d'une version DataHub, hors
CI, démarre un vrai serveur (voir « Élargir la plage des versions DataHub »).

## Structure du projet

Le pipeline est linéaire, orchestré par `pipeline.py` (pas par `cli.py`, qui
ne fait que traduire ses outcomes en présentation terminal :

```
reader/  →  mapping/  →  validate/  →  emit/
             ↑ orchestré par pipeline.py, consommé par cli.py et les tests
```

- **`reader/`** — lit un DataProduct DataHub (`DataHubGraph.get_entity_semityped()`,
  structured properties, aspect timeseries `datasetProfile`) et le convertit
  en modèle pivot (`model.py`).
- **`mapping/`** — convertit le modèle pivot en triples RDF HealthDCAT-AP
  (namespaces, vocabulaires contrôlés dans `mapping/vocab/*.yml`, `agent.py`,
  `dataset.py`, `distribution.py`).
- **`validate/`** — valide le graphe RDF produit contre les shapes SHACL
  réelles du HDH (`shapes/ehds/`).
- **`emit/`** — sérialise le graphe vers un fichier (Turtle, JSON-LD,
  N-Triples), pousse vers `/ingest/datasets` du HDH (`hdh_client.py`), et
  porte l'état de poussée durable (`state.py::PushState`), cloisonné par
  instance.
- **`config.py`** — résout l'instance de destination de `push-hdh` (URL, clé)
  par profils nommés déclarés dans `.dh-healthdcat.yml`. Séparé en deux :
  chargement (I/O sur le fichier YAML) et résolution (fonction pure,
  `resolve_target`, sans accès à `os.environ` — l'environnement lui est
  injecté), pour rester testable hors ligne sans `monkeypatch`.
- **`pipeline.py`** — orchestre les quatre étapes ci-dessus et produit une
  séquence d'outcomes typés (`Prepared`/`Unreadable`/`Rejected` pour
  `prepare()`, plus `Pushed`/`Planned`/`PushFailed` pour `push()`) : c'est le
  seul seam traversé par `export-file`, `push-hdh` et les tests
  (`tests/unit/test_pipeline.py`, `test_push.py`).

Le mapping DataHub ↔ HealthDCAT-AP (avec ses justifications) est documenté
dans [`docs/mapping.md`](docs/mapping.md) — à tenir à jour avec tout
changement de correspondance de champs.

## Style de commit

Ce dépôt suit le format [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>[scope optionnel]: <description>

[corps optionnel]

Signed-off-by: Prénom Nom <email>
```

Types autorisés : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `deps`. Sujet à
l'impératif, ≤ 72 caractères, sans point final. Scopes libres.

### Signoff DCO

Chaque commit doit porter un trailer `Signed-off-by:` attestant du
[Developer Certificate of Origin](https://developercertificate.org/). Il
s'ajoute automatiquement avec :

```bash
git commit -s
```

### Historique de branche propre

`main` n'accepte que le **merge par rebase** (ni commit de merge, ni squash ;
historique linéaire exigé) : **tous** les commits de la branche atterrissent
tels quels sur `main` et sont lus par release-please pour le calcul de version
et le changelog. Avant d'ouvrir la PR, nettoyez l'historique de la branche
(rebase interactif) pour que chaque commit soit atomique et son message exact.
Pour rattraper `main`, rebasez la branche (« Update with rebase ») plutôt que
d'y fusionner `main`.

Vérifié en CI (`.github/workflows/commit-policy.yml`) : `commitlint` sur
chaque commit, `dco` pour le signoff. Le titre de PR n'est pas vérifié : il
n'entre pas dans l'historique.

## Lancer un serveur DataHub local

Pour inspecter une version du serveur à la main, sans seed ni export :

```bash
scripts/datahub-local.sh 1.7.0 up            # UI http://localhost:9002 (datahub / datahub)
scripts/datahub-local.sh 1.7.0 down          # arrêt, données conservées
scripts/datahub-local.sh 1.7.0 down --purge  # suppression, volumes compris
```

Chaque version a son projet compose (`dhhc-local-<version>`) et ses propres
volumes, distincts de ceux du contrôle Docker et de tout quickstart par défaut
(`datahub_*`). Une seule version tourne à la fois, sur les ports par défaut :
`up` refuse de démarrer si un autre serveur répond déjà sur 8080. Un `up`
suivant redémarre la même instance sur ses données.

N'utilisez pas `datahub docker nuke` : quel que soit le projet, il supprime
aussi les volumes `datahub_mysqldata`, `datahub_broker`… d'un quickstart par
défaut.

### Sous Windows

Les scripts `scripts/*.sh` se lancent avec **Git Bash** (fourni avec Git pour
Windows), depuis la racine du dépôt, avec Docker Desktop démarré. Ils utilisent
`uv` et `docker` de Windows et le `.venv` du projet.

Depuis un terminal Git Bash :

```bash
scripts/datahub-local.sh 1.7.0 up
```

Depuis PowerShell, appelez Git Bash par son chemin complet :

```powershell
& "C:\Program Files\Git\bin\bash.exe" scripts/datahub-local.sh 1.7.0 up
```

**Ne tapez pas `bash` seul dans PowerShell ou cmd.** Cette commande lance
`C:\Windows\System32\bash.exe`, le bash de **WSL**. Le script tournerait
alors dans la distribution Linux, avec son propre `uv`, sans le `.venv` du
projet, et éventuellement face au moteur Docker de WSL, celui d'un quickstart
que vous y auriez lancé. Pour vérifier lequel vous appelez :
`Get-Command bash -All` dans PowerShell.

## Élargir la plage des versions DataHub

La plage des *Versions DataHub supportées* fait foi dans `pyproject.toml`
(contrainte `acryl-datahub`) et ne contient que des versions vérifiées
(`docs/adr/0004-support-versions-datahub.md`). Une nouvelle mineure du serveur
(1.8, 1.9…) n'y entre que par une PR d'élargissement, revue humainement, qui
exige le contrôle Docker local. Il n'est jamais lancé en CI.

Les montées de patch (`1.7.0.x → 1.7.0.y`) ne sont pas concernées : Dependabot
les classe `semver-patch` et elles restent en auto-merge, sans contrôle Docker.

### Prérequis

- Docker, avec environ 8 Go de RAM disponibles.
- Sous Windows : Git Bash, pas le `bash` de WSL (voir « Sous Windows »
  ci-dessus).
- Les ports 8080, 9002, 3306, 9092 et 9200 libres : **arrêtez tout autre
  quickstart DataHub** avant de lancer le contrôle (`docker compose -p datahub
  stop` conserve ses données). Le script refuse de démarrer si un serveur répond
  déjà sur 8080.

Le script isole ses données dans des volumes propres à la version
(`dhhc-verify-<version>_*`) et les supprime à la fin. Ne lancez pas
`datahub docker quickstart --version …` à la main pour ce contrôle : le compose
du quickstart nomme ses volumes en dur (`datahub_*`), et un serveur d'une
autre version démarrerait sur les données de votre instance locale.

### Procédure

1. Dans la PR d'élargissement (ouverte par Dependabot ou à la main), porter le
   plafond de la contrainte à la mineure suivante (`acryl-datahub>=1.7,<1.9`
   pour accueillir la 1.8), puis `uv lock`. Le plafond doit rester la dernière
   mineure vérifiée.
2. Lancer le contrôle contre la nouvelle version du serveur :

   ```bash
   scripts/verify-datahub-version.sh 1.8.0
   ```

   Il démarre le serveur, charge les définitions des SP
   (`dh-healthdcat properties`) et le seed de `tests/integration/seed/`, exporte
   le DataProduct, le valide contre la sensitivity shape et le compare par
   isomorphisme RDF à `tests/integration/expected/datahub-<mineure>.ttl`.
   Comptez une dizaine de minutes. `--keep` laisse le serveur tourner pour
   l'inspecter.
3. Lire le résultat :
   - **Sortie 0** : export conforme et identique à la référence.
   - **Échec SHACL** : l'export n'est plus conforme sur cette version. C'est
     une incompatibilité à corriger, dans `reader/graph.py` seulement (seule
     frontière avec DataHub, ADR-0004 §4).
   - **Écart avec la référence** : le diff liste les triples présents d'un seul
     côté (`-` référence, `+` export). Chaque écart est soit une régression à
     corriger, soit un changement voulu à expliquer dans la PR.
4. Pour une mineure qui n'a pas encore de référence, ou quand un écart est
   voulu, régénérer la référence puis la commiter dans la PR :

   ```bash
   scripts/verify-datahub-version.sh 1.8.0 --update-reference
   ```

   Relancer ensuite le contrôle sans l'option : un second passage sur un
   serveur neuf doit donner un graphe identique. Si une valeur dépend du moment
   de l'ingestion, la normaliser dans `scripts/compare_reference.py` et
   documenter pourquoi.
5. Cocher la case « contrôle Docker passé sur X.Y » du modèle de PR.

## Avant de proposer une modification

1. `uv run pytest` doit passer.
2. Toute nouvelle correspondance de champ DataHub → HealthDCAT-AP doit être
   reflétée dans `docs/mapping.md`.
3. Si le changement touche un vocabulaire contrôlé (`mapping/vocab/*.yml`),
   vérifier la valeur exacte attendue par les shapes SHACL du HDH plutôt que
   de supposer l'identifiant DPV/DCAT-AP nu (voir `mapping/vocab/README.md`).
