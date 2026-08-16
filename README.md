# datahub-healthdcat-ap-exporter

Exporte les métadonnées de l'Entrepôt de Données de Santé (EDS) AP-HP, cataloguées dans [DataHub](https://datahubproject.io/), vers le standard [HealthDCAT-AP](https://healthdcat-ap.github.io/) — en fichier Turtle ou directement vers l'API du [catalogue de métadonnées du Health Data Hub](https://health-data-hub.fr/).

## Principe

Un **DataProduct** DataHub devient un `dcat:Dataset` HealthDCAT-AP. Ses assets (Datasets DataHub) deviennent des `dcat:distribution` — ou des `adms:sample` s'ils portent le tag `dcat:sample`. Le schéma de chaque asset (`schemaMetadata`) devient une `csvw:Table`/`csvw:Column`.

Le mapping complet, avec ses justifications et les corrections apportées en cours d'implémentation (vérifiées contre les shapes SHACL réelles du HDH), est documenté dans [`docs/mapping.md`](docs/mapping.md).

```
DataHub GMS
    │  DataHubGraph.get_entity_semityped()
    ▼
┌─────────────┐   modèle pivot     ┌──────────────┐   rdflib.Graph   ┌───────────────┐
│  reader/    │ ─── dataclasses ─▶│   mapping/   │ ──── triples ───▶│  emit/        │
│ (extraction)│   HealthDataset    │ (traduction) │                  │(sérialisation)│
└─────────────┘                    └──────────────┘                  └──────┬────────┘
                                          │                                 │
                                  validate/ (SHACL)                         ├─▶ fichier .ttl
                                  pyshacl, avant tout envoi                 └─▶ POST /ingest (HDH)
```

## Installation

```bash
uv venv .venv
uv pip install -e ".[dev]"
```

### Configuration DataHub

`dh-healthdcat` se connecte au GMS via `DataHubGraph.get_default_graph()` — exactement la même résolution que la CLI `datahub` elle-même. Si `datahub` (ou tout script `acryl-datahub`) fonctionne déjà sur ce poste, `dh-healthdcat` fonctionnera sans configuration supplémentaire.

Deux façons de configurer la connexion, par ordre de priorité :

1. **Variables d'environnement** — prioritaires sur le fichier de config :
   ```bash
   export DATAHUB_GMS_URL=http://localhost:8080
   export DATAHUB_GMS_TOKEN=...   # si l'instance exige une authentification
   ```
2. **`~/.datahubenv`** — créé par `datahub init` (mode interactif : demande l'URL du GMS et un jeton d'accès) :
   ```yaml
   gms:
     server: http://localhost:8080
     token: ''
   ```

Référence officielle : [DataHub CLI — docs.datahub.com/docs/cli](https://docs.datahub.com/docs/cli).

Ne pas confondre avec la configuration du **HDH** (`--hdh-url`/`--api-key` de `push-hdh`, voir plus bas) : DataHub est la source lue, le HDH est la destination poussée.

## Usage

### Export en fichier Turtle

```bash
dh-healthdcat export-file --output catalogue.ttl
dh-healthdcat export-file --urn urn:li:dataProduct:b78435bfad26dab4c11e6e41c2a72b53 --output un-jeu.ttl
dh-healthdcat export-file --domain "Biologie" --tag eds --format json-ld --split-per-dataset out/
dh-healthdcat export-file --tag eds --tag urgences --tag-mode all --exclude-tag dcat:sample --output prod.ttl
```

Chaque DataProduct est validé individuellement contre les shapes SHACL du HDH (`shapes/ehds/`) ; un jeu invalide (champ obligatoire manquant ou violation SHACL) est **exclu de l'export, pas l'export entier** — les autres DataProducts sélectionnés sont écrits normalement (`--no-strict` pour l'inclure quand même malgré ses erreurs, utile en exploration). Le code de sortie reste non nul dès qu'au moins un jeu a été exclu, même si le fichier produit contient les autres. Un jeu invalide produit un message explicite :

```
ERREUR: DataProduct "Imagerie médicale" : healthdcatap:healthTheme manquant → renseigner fr.aphp.healthdcat.healthTheme
  -> "Imagerie médicale" exclu de l'export : erreurs ci-dessus (--no-strict pour forcer)
```

**Sémantique de sélection** (`--domain`/`--tag`/`--tag-mode`/`--exclude-tag`, partagée par `export-file` et `push-hdh`, évaluée côté serveur en une seule requête de recherche — voir `spec/spec-feature-tag-filtering.md`) :

- Plusieurs `--domain` sont combinés en OU (au moins un des domaines).
- Plusieurs `--tag` sont combinés en OU par défaut (`--tag-mode any`) ; `--tag-mode all` exige la présence de tous les tags donnés.
- `--exclude-tag` (répétable) retire tout DataProduct portant l'un des tags exclus, quels que soient les autres critères.
- `--domain` et `--tag`/`--exclude-tag` entre eux sont combinés en ET.
- `--urn` est **prioritaire** : s'il est fourni, les DataProducts nommés sont traités tels quels et `--domain`/`--tag`/`--exclude-tag` sont ignorés (un avertissement est émis s'ils sont fournis en même temps).

### Valider un fichier RDF isolé

```bash
dh-healthdcat validate catalogue.ttl
dh-healthdcat validate export.jsonld --format json-ld
```

Indépendant de DataHub — utile pour un fichier édité à la main, produit par un autre outil, ou récupéré du HDH. Code de sortie 0 si conforme, 1 sinon (rapport SHACL affiché).

### Poussée vers le catalogue HDH

```bash
export HDH_API_KEY=mdc_...
dh-healthdcat push-hdh --hdh-url https://catalogue.health-data-hub.fr --dry-run
dh-healthdcat push-hdh --hdh-url https://catalogue.health-data-hub.fr
```

Idempotent : une correspondance URN DataHub → id HDH est conservée (`.dh-healthdcat-state.json` par défaut) pour mettre à jour un jeu déjà poussé plutôt que d'en créer un doublon. Aucune requête réseau n'est émise pour un jeu qui ne passe pas la validation SHACL.

L'état est écrit sur disque immédiatement après chaque jeu poussé avec succès (écriture atomique), pas seulement à la fin du lot : une poussée interrompue (Ctrl-C, coupure réseau) reprend sans dupliquer les jeux déjà envoyés.

## Structure du dépôt

```
src/dh_healthdcat/
  cli.py                  # commandes export-file / validate / push-hdh (Typer), présentation seulement
  pipeline.py              # orchestration lecture→mapping→validation→décision, outcomes typés
  model.py                # modèle pivot (HealthDataset, Distribution, Agent...)
  selection.py            # filtres --urn/--domain/--tag, partagés par les deux commandes
  reader/                  # DataHub → modèle pivot
  mapping/                 # modèle pivot → triples RDF, vocabulaires contrôlés
  emit/                    # sérialisation fichier, client API HDH, état de poussée durable
  validate/                # validation SHACL (shapes empaquetées)
shapes/ehds/                # copie de référence des shapes SHACL du HDH
tests/                      # tests unitaires, fixtures sans dépendance réseau
docs/mapping.md              # documentation vivante du mapping
```

## Tests

```bash
uv run pytest
```

Aucun test ne nécessite d'instance DataHub ou HDH : le reader est testé contre un double (`tests/fixtures/fake_datahub.py`), le mapping et la validation SHACL contre des graphes construits à la main.

## Statut

Les Lots 1 (mapping), 2 (export fichier) et 3 (poussée API) sont implémentés et testés. Reste à faire avant un usage en production :

- **Curation** — peupler les nouvelles propriétés `fr.aphp.healthdcat.*` sur les DataProducts existants (`aphp/datahub-sample`, Phase 0 déjà étendue). Un DataProduct de test entièrement conforme (`test-healthdcat-ap-sample`, dans `dataproduct-layer/assets.yml`, `dcat:byteSize` inclus via un aspect `datasetProfile`) sert de référence — validé de bout en bout via le connecteur d'ingestion réel (`aphp/datahub-yaml-source`), voir `docs/mapping.md`.
- **URIs de production** — `HealthCategories`/`HealthTheme` pointent sur un hôte de développement HDH en dur, à reconfirmer avant publication.
