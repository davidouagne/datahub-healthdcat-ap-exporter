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
ligne de la même façon.

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

Types autorisés : `feat`, `fix`, `test`, `docs`, `chore`, `build`. Sujet à
l'impératif, ≤ 72 caractères, sans point final. Scopes libres.

### Signoff DCO

Chaque commit doit porter un trailer `Signed-off-by:` attestant du
[Developer Certificate of Origin](https://developercertificate.org/). Il
s'ajoute automatiquement avec :

```bash
git commit -s
```

### Historique de branche propre

`main` n'accepte que le **merge par commit de merge** (pas de squash, pas de
rebase-merge) : **tous** les commits de la branche atterrissent sur `main` et
sont lus par release-please pour le calcul de version et le changelog. Avant
d'ouvrir la PR, nettoyez l'historique de la branche (rebase interactif) pour
que chaque commit soit atomique et son message exact.

Vérifié en CI (`.github/workflows/commit-policy.yml`) : `commitlint` sur
chaque commit non-merge, `dco` pour le signoff, et le titre de PR (futur
sujet du commit de merge) doit lui aussi être un Conventional Commit valide.

## Avant de proposer une modification

1. `uv run pytest` doit passer.
2. Toute nouvelle correspondance de champ DataHub → HealthDCAT-AP doit être
   reflétée dans `docs/mapping.md`.
3. Si le changement touche un vocabulaire contrôlé (`mapping/vocab/*.yml`),
   vérifier la valeur exacte attendue par les shapes SHACL du HDH plutôt que
   de supposer l'identifiant DPV/DCAT-AP nu (voir `mapping/vocab/README.md`).
