# datahub-healthdcat-ap-exporter

[![CI](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/davidouagne/datahub-healthdcat-ap-exporter/graph/badge.svg)](https://codecov.io/gh/davidouagne/datahub-healthdcat-ap-exporter)
[![PyPI](https://img.shields.io/pypi/v/dh-healthdcat.svg)](https://pypi.org/project/dh-healthdcat/)
[![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://pypi.org/project/dh-healthdcat/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Exporte des jeux de données de santé catalogués dans [DataHub](https://datahubproject.io/) vers le standard [HealthDCAT-AP](https://healthdcat-ap.github.io/) — en fichier Turtle ou directement vers l'API du [Catalogue de métadonnées de la Plateforme des Données de Santé](https://catalogue-metadonnees.health-data-hub.fr/) (HDH).

L'outil s'adresse à tout **adoptant** : un entrepôt ou un producteur de données de santé qui catalogue ses jeux dans DataHub et veut les publier en HealthDCAT-AP. Il lit DataHub sans jamais y écrire.

## Principe

Un **DataProduct** DataHub devient un `dcat:Dataset` HealthDCAT-AP. Ses assets (Datasets DataHub) deviennent des `dcat:distribution` — ou des `adms:sample` s'ils portent le tag `dcat:sample`. Si le DataProduct déclare des output ports, seuls ces ports deviennent des distributions. Le schéma de chaque asset (`schemaMetadata`) devient une `csvw:Table`/`csvw:Column`.

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

## Démarrage rapide

Parcours d'un nouvel adoptant, de l'installation au premier export. Chaque étape est détaillée plus bas.

1. **Installer** l'outil, dans un environnement qui accède à votre DataHub :
   ```bash
   pip install dh-healthdcat
   ```
2. **Se connecter à DataHub** : `dh-healthdcat` réutilise la configuration de la CLI `datahub` (`DATAHUB_GMS_URL`/`DATAHUB_GMS_TOKEN` ou `~/.datahubenv`, voir « Configuration DataHub »).
3. **Créer les structured properties** que l'exporteur lit :
   ```bash
   dh-healthdcat properties --output structured-properties.yml
   datahub properties upsert -f structured-properties.yml
   ```
4. **Déclarer l'URI de base**, l'espace de noms HTTP sous lequel l'exporteur forge les identifiants de vos jeux, dans `.dh-healthdcat.yml` :
   ```yaml
   profiles:
     dev:
       url: https://dev.catalogue.health-data-hub.fr
       base_uri: https://example.org
   ```
5. **Renseigner les SP `healthdcatap.*`** sur vos DataProducts (UI DataHub, `datahub dataproduct upsert`, ou votre propre connecteur). `docs/mapping.md` indique les propriétés obligatoires.
6. **Exporter, vérifier, puis pousser** :
   ```bash
   dh-healthdcat export-file --output catalogue.ttl
   dh-healthdcat validate catalogue.ttl
   export HDH_API_KEY=mdc_...   # clé data-provider du catalogue HDH
   dh-healthdcat push-hdh --dry-run
   ```

## Installation

```bash
pip install dh-healthdcat
```

Pour contribuer (installation éditable, outils de développement) :

```bash
uv venv .venv
uv pip install -e ".[dev]"
```

### Versions DataHub supportées

La plage des versions du serveur DataHub (GMS) supportées fait foi dans
`pyproject.toml`, contrainte `acryl-datahub` : la version du client installé et
celle du serveur visé suivent la même plage. Elle ne contient que des versions
vérifiées ; une mineure plus récente n'y entre qu'après vérification (voir
`docs/adr/0004-support-versions-datahub.md`).

Au démarrage, `export-file` et `push-hdh` lisent la version du serveur sur
`/config`. Hors plage, version non reconnue ou DataHub Cloud : un
avertissement, et la commande continue. Avec `--strict-version`, ces mêmes cas
la font échouer (code 1), avant toute lecture du catalogue.

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

### Définitions des structured properties

L'exporteur lit ses métadonnées dans des structured properties (SP) DataHub. Leurs définitions (type, cardinalité, valeurs autorisées, types d'entités) sont livrées avec le paquet, et correspondent exactement à la version installée :

```bash
dh-healthdcat properties --output structured-properties.yml
datahub properties upsert -f structured-properties.yml
```

Toutes les SP sont préfixées `healthdcatap.` (ADR-0005). L'ancien préfixe `fr.aphp.healthdcat.` n'est plus lu : sur une instance qui ne définit que celui-ci, `export-file` et `push-hdh` s'arrêtent au lancement avec une erreur unique qui renvoie au guide de migration.

Les valeurs autorisées sont celles des vocabulaires que l'exporteur sait résoudre. `dh-healthdcat` n'écrit jamais dans DataHub : c'est vous qui appliquez le fichier, et vous pouvez restreindre ces valeurs dans votre propre registre.

Ne pas confondre avec la configuration du **Catalogue de métadonnées de la PDS** (`--hdh-url`/`--api-key` de `push-hdh`, voir plus bas) : DataHub est la source lue, le Catalogue de métadonnées est la destination poussée.

## Usage

### Export en fichier Turtle

```bash
dh-healthdcat export-file --base-uri https://example.org --output catalogue.ttl
dh-healthdcat export-file --urn urn:li:dataProduct:b78435bfad26dab4c11e6e41c2a72b53 --output un-jeu.ttl
dh-healthdcat export-file --domain "Biologie" --tag publiable --format json-ld --split-per-dataset out/
dh-healthdcat export-file --tag publiable --tag urgences --tag-mode all --exclude-tag dcat:sample --output prod.ttl
```

L'URI de base est obligatoire : `--base-uri`, ou `base_uri` dans le profil du fichier de configuration (voir « Configuration de l'instance »). Les exemples suivants supposent qu'un profil la déclare.

Chaque DataProduct est validé individuellement contre les shapes SHACL du HDH (`shapes/ehds/`) ; un jeu invalide (champ obligatoire manquant ou violation SHACL) est **exclu de l'export, pas l'export entier** — les autres DataProducts sélectionnés sont écrits normalement (`--no-strict` pour l'inclure quand même malgré ses erreurs, utile en exploration). Le code de sortie reste non nul dès qu'au moins un jeu a été exclu, même si le fichier produit contient les autres. Un jeu invalide produit un message explicite :

```
ERREUR: DataProduct "Imagerie médicale" : healthdcatap:healthTheme manquant → renseigner healthdcatap.healthTheme
  -> "Imagerie médicale" exclu de l'export : erreurs ci-dessus (--no-strict pour forcer)
```

**Sémantique de sélection** (`--domain`/`--tag`/`--tag-mode`/`--exclude-tag`, partagée par `export-file` et `push-hdh`, évaluée côté serveur en une seule requête de recherche) :

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

L'état est écrit sur disque immédiatement après chaque jeu poussé avec succès (écriture atomique), pas seulement à la fin du lot : une poussée interrompue (Ctrl-C, coupure réseau) reprend sans dupliquer les jeux déjà envoyés. L'état est cloisonné par instance (par URL normalisée) : pousser vers deux instances avec le même `--state-file` ne mélange jamais leurs ids.

#### Configuration de l'instance (profils)

Plutôt que de retaper `--hdh-url` à chaque appel, déclarer une fois ses instances dans `.dh-healthdcat.yml` (répertoire courant ou `~`, committable — **aucun secret n'y figure**) :

```yaml
default_profile: dev
profiles:
  dev:
    url: https://dev.catalogue.health-data-hub.fr
  preprod:
    url: https://preprod.catalogue.health-data-hub.fr
    api_key_env: HDH_API_KEY_PREPROD   # variable dédiée, optionnel (sinon HDH_API_KEY)
  prod:
    url: https://catalogue.health-data-hub.fr
    base_uri: https://example.org   # URI de base de l'adoptant
```

```bash
dh-healthdcat push-hdh --profile preprod --dry-run
dh-healthdcat push-hdh --profile prod
```

Un nom de profil inconnu est toujours une erreur qui liste les profils déclarés (code de sortie 2) — jamais un repli silencieux sur un défaut, pour qu'une faute de frappe ne puisse jamais viser la production. Le fichier lui-même rejette toute clé `api_key:` en clair : un profil ne déclare qu'un *nom* de variable d'environnement (`api_key_env`).

Résolution par champ, chacun indépendamment, du plus prioritaire au moins prioritaire :

| Champ | Précédence |
|---|---|
| URL | `--hdh-url` `>` `$HDH_URL` `>` `url` du profil sélectionné |
| Profil | `--profile` `>` `$HDH_PROFILE` `>` `default_profile` du fichier `>` l'unique profil s'il n'y en a qu'un |
| Fichier de config | `--config` `>` `$HDH_CONFIG` `>` `./.dh-healthdcat.yml` `>` `~/.dh-healthdcat.yml` (premier trouvé, pas de fusion) |
| Variable de clé API | `--api-key-env` `>` `api_key_env` du profil `>` `HDH_API_KEY` |
| URI de base | `--base-uri` `>` `base_uri` du profil sélectionné — **obligatoire**, sans valeur par défaut |

L'**URI de base** est l'espace de noms HTTP de l'adoptant : l'exporteur y forge `dct:identifier` (`<base>/dataset/<id>`) et les spécifications de référence qu'aucun vocabulaire ne résout (`<base>/conformsTo/<code>`). `export-file` et `push-hdh` la lisent dans le profil (`--config`/`--profile` valent aussi pour `export-file`) ou via `--base-uri`. Sans l'une ni l'autre, la commande s'arrête avant tout appel réseau (code de sortie 2).

Sans fichier de configuration, `push-hdh --hdh-url … --base-uri …` (clé dans `$HDH_API_KEY`) fonctionne comme avant.

## Structure du dépôt

```
src/dh_healthdcat/
  cli.py                   # commandes export-file / validate / push-hdh / properties (Typer), présentation seulement
  sp.py, sp_definitions.*  # préfixe et définitions canoniques des structured properties
  pipeline.py              # orchestration lecture→mapping→validation→décision, outcomes typés
  model.py                 # modèle pivot (HealthDataset, Distribution, Agent...)
  selection.py             # filtres --urn/--domain/--tag, partagés par les deux commandes
  config.py                # résolution de l'instance du Catalogue de métadonnées (profils)
  reader/                  # DataHub → modèle pivot
  mapping/                 # modèle pivot → triples RDF, vocabulaires contrôlés
  emit/                    # sérialisation fichier, client API HDH, état de poussée durable
  validate/                # validation SHACL (shapes empaquetées)
shapes/ehds/               # copie de référence des shapes SHACL du HDH
tests/                     # tests unitaires, fixtures sans dépendance réseau
docs/mapping.md            # documentation vivante du mapping
```

## Tests

```bash
uv run pytest
```

Aucun test ne nécessite d'instance DataHub ou d'instance Catalogue de métadonnées de la PDS : le reader est testé contre un double (`tests/fixtures/fake_datahub.py`), le mapping et la validation SHACL contre des graphes construits à la main.

## Statut

Implémentés et testés : le mapping, l'export fichier, la poussée API avec idempotence, et la configuration de l'instance par profils avec état cloisonné (voir « Configuration de l'instance » ci-dessus). `push-hdh` a été validé de bout en bout contre une instance HDH locale réelle le 2026-08-16 : jeu créé, `.dh-healthdcat-state.json` écrit au format v2 cloisonné par instance.

## Origine

L'exporteur est né à l'AP-HP, pour publier les métadonnées de son Entrepôt de Données de Santé (EDS) vers le Catalogue HDH. L'AP-HP en est l'**adoptant d'origine**, pas un cas particulier du code : depuis la 0.3.0 (ADR-0005), les structured properties portent un préfixe neutre (`healthdcatap.*`), leurs définitions sont publiées par ce dépôt, et l'URI de base se déclare explicitement. Un catalogue qui utilise encore l'ancien préfixe `fr.aphp.healthdcat.*` doit suivre le guide de migration (`docs/migration-0.3.0.md`).

Côté AP-HP, les DataProducts sont ingérés dans DataHub par un connecteur maison (`datahub-yaml-source`). Leur curation (peupler les `healthdcatap.*`) reste à faire pour la plupart : sans ces propriétés, un DataProduct est exclu de tout export strict.
