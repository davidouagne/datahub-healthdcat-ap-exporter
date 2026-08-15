# Contribuer à dh-healthdcat

## Mise en place de l'environnement

```bash
uv venv
uv pip install -e ".[dev]"
```

Sans `uv`, un `venv` standard fonctionne aussi :

```bash
python -m venv .venv
.venv/Scripts/activate  # ou source .venv/bin/activate sous Linux/macOS
pip install -e ".[dev]"
```

## Lancer les tests

```bash
uv run pytest
```

Aucun test ne nécessite d'instance DataHub ou HDH réelle : le `reader` est
testé contre un double (`tests/fixtures/fake_datahub.py`), le `mapping` et la
validation SHACL contre des graphes construits à la main. Toute contribution
touchant à la lecture DataHub ou au mapping RDF doit rester testable hors
ligne de la même façon.

## Structure du projet

Le pipeline est linéaire, orchestré par `cli.py` :

```
reader/  →  mapping/  →  validate/  →  emit/
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
  N-Triples) ou le pousse vers `/ingest/datasets` du HDH.

Le mapping DataHub ↔ HealthDCAT-AP (avec ses justifications) est documenté
dans [`docs/mapping.md`](docs/mapping.md) — à tenir à jour avec tout
changement de correspondance de champs.

## Style de commit

Ce dépôt suit le format [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>[scope optionnel]: <description>

[corps optionnel]
```

Types utilisés : `feat`, `fix`, `test`, `docs`, `chore`. Sujet à l'impératif,
≤ 72 caractères, sans point final.

## Avant de proposer une modification

1. `uv run pytest` doit passer.
2. Toute nouvelle correspondance de champ DataHub → HealthDCAT-AP doit être
   reflétée dans `docs/mapping.md`.
3. Si le changement touche un vocabulaire contrôlé (`mapping/vocab/*.yml`),
   vérifier la valeur exacte attendue par les shapes SHACL du HDH plutôt que
   de supposer l'identifiant DPV/DCAT-AP nu (voir `mapping/vocab/README.md`).
