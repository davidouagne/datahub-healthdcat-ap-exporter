# PRD — Paramétrer l'instance du Catalogue de métadonnées

**Statut** : implémenté. Les références `fichier:ligne` datent de la rédaction.
**Date** : 2026-08-16
**Auteur** : David Ouagne

## Problem Statement

`push-hdh` écrit vers le Catalogue de métadonnées de la Plateforme des Données de
Santé. L'instance visée n'est pas configurable : elle se retape à chaque appel.

**1. `--hdh-url` est une option obligatoire, sans repli.**
`cli.py:175` la déclare en `typer.Option(...)`. Il n'existe ni variable
d'environnement ni fichier de configuration pour la porter. La seule variable
d'environnement que le projet lise est `os.environ.get(api_key_env)`
(`cli.py:198`) — il n'y a **aucun module de configuration** dans le dépôt.
L'asymétrie avec la source est frappante et déjà visible dans le README : DataHub
se configure par `DATAHUB_GMS_URL`/`~/.datahubenv` (`README.md:31-51`), la
destination par une option à retaper.

**2. Passer d'une instance à l'autre n'a aucun garde-fou.**
Dev, préprod et prod se distinguent par une URL tapée à la main. Une faute de
frappe ou un copier-coller d'historique shell suffit pour pousser des métadonnées
vers la mauvaise instance. Il n'existe aucun moyen de déclarer une fois pour toutes
les instances légitimes et de les désigner par un nom.

**3. L'état de poussée n'est pas cloisonné par instance — et devient dangereux dès
que l'instance est un paramètre.**
`PushState` (`emit/state.py:21-46`) est un mapping **plat** `{urn DataHub: id}`
persisté dans un fichier unique par défaut (`.dh-healthdcat-state.json`,
`state.py:18`). Or ces ids sont attribués par une instance donnée. Avec le même
fichier d'état, pousser vers prod après avoir poussé vers dev émet
`PUT /ingest/datasets/origin?originalId=<id de dev>` : 404 au mieux, mise à jour
d'un jeu étranger au pire. Le problème existe déjà aujourd'hui, mais rendre
l'instance paramétrable le transforme d'accident improbable en mode d'échec
courant.

Qui est affecté : tout exploitant poussant vers plus d'une instance (le cas normal
dès qu'une préprod existe), et toute automatisation CI future, qui devrait
aujourd'hui porter l'URL en dur dans le workflow.

## Goals

- L'instance de destination se déclare **une fois** (profil nommé) et se désigne
  ensuite par son nom, au lieu d'être retapée en URL à chaque invocation.
- La configuration est résoluble sans secret versionné : le fichier de
  configuration est fait pour être commité et ne contient aucune clé API.
- Un changement d'instance ne peut plus corrompre l'idempotence : l'état de
  poussée est cloisonné par instance, avec reprise transparente de l'état existant.
- La résolution de configuration est testable hors ligne, sans réseau, sans
  instance réelle et sans détournement d'`os.environ` — même contrainte que le
  reste du dépôt (`CONTRIBUTING.md:24-28`).
- Aucune invocation existante ne change de comportement.

## Non-Goals

- **Configurer DataHub (la source) depuis la CLI** — `reader/graph.py:129-134`
  expose déjà `from_config(server, token)`, inutilisée ; l'y raccorder est un
  périmètre séparé, symétrique mais distinct.
- **Rendre configurables les chemins d'endpoints REST** (`/ingest/datasets`,
  `/ingest/datasets/origin`, `/api-keys/whoami`) ni un préfixe d'API : ils restent
  en dur dans `emit/hdh_client.py`.
- **Renommer « HDH » en « Catalogue de métadonnées » dans le code**
  (`push-hdh`, `HdhClient`, `hdh_client.py`, `HDH_API_KEY`, `hdh_id_for`,
  `pipeline.Pushed.hdh_id`) — décision prise : **ce lot n'ajoute que du nouveau**,
  et les ajouts suivent le nommage existant. Un renommage large noierait la revue
  de la fonctionnalité dans un diff mécanique.
- **Dériver les URI d'autorité des vocabulaires de l'URL d'instance** —
  `HealthCategories.yml`/`HealthTheme.yml` pointent sur `http://13.81.34.152:1101/`
  parce que ce sont des copies conformes des dictionnaires du HDH ; c'est la
  question ouverte Q1 documentée dans `mapping/vocab/README.md:18-22`, où « le HDH
  fait foi ». Hors périmètre.

## User Stories

**Exploitant du catalogue**
- En tant qu'exploitant, je veux déclarer une fois mes instances dev/préprod/prod
  et pousser avec `--profile preprod`, afin de ne plus dépendre d'une URL retapée
  ou repêchée dans l'historique shell.
- En tant qu'exploitant, je veux qu'un nom de profil inconnu échoue en listant les
  profils existants, plutôt que de retomber silencieusement sur un défaut — une
  faute de frappe ne doit jamais pouvoir viser la production.

**Intégrateur CI**
- En tant qu'intégrateur, je veux que l'URL de destination vienne d'un fichier
  versionné et la clé d'une variable d'environnement (secret CI), afin de ne rien
  avoir à coder en dur dans un workflow ni à commiter de secret.

**Exploitant multi-instances**
- En tant qu'exploitant poussant vers deux instances, je veux que les ids attribués
  par l'une ne soient jamais réutilisés contre l'autre, afin de ne pas créer de
  doublons ni de mettre à jour un jeu étranger.

**Utilisateur existant**
- En tant qu'utilisateur ayant déjà poussé, je veux que ma mise à jour ne me fasse
  pas repartir de zéro : mes correspondances URN→id existantes doivent continuer de
  s'appliquer à l'instance vers laquelle je poussais.

**Mainteneur du projet**
- En tant que mainteneur, je veux que la précédence de configuration soit couverte
  par des tests hors ligne, afin qu'une régression soit détectée par
  `uv run pytest` et pas par une poussée vers la mauvaise instance.

## Requirements

### Must-Have (P0)

| ID | Exigence | Critère d'acceptation |
|----|----------|------------------------|
| REQ-001 | L'URL de base est résolue par précédence : `--hdh-url` > `$HDH_URL` > `url` du profil sélectionné | Given un profil déclarant `url: A`, When `--hdh-url B` est passé, Then B est utilisée. Given aucune option, When `$HDH_URL=C`, Then C est utilisée. Given ni option ni variable, Then l'URL du profil est utilisée |
| REQ-002 | La configuration se déclare dans un fichier YAML à profils nommés, cherché dans `./.dh-healthdcat.yml` puis `~/.dh-healthdcat.yml` (premier trouvé gagne, **pas de fusion**), surchargeable par `--config`/`$HDH_CONFIG` | Given un fichier dans le répertoire courant et un autre dans le home, When la configuration est chargée, Then seul le fichier courant est lu et son chemin est celui cité dans les messages d'erreur |
| REQ-003 | Le fichier ne peut porter **aucun secret** : un profil déclare un *nom* de variable (`api_key_env`), et une clé `api_key:` en clair est **rejetée** par une erreur, pas ignorée | Given un profil contenant `api_key: mdc_...`, When la configuration est chargée, Then une erreur nomme le profil et le fichier et renvoie vers `api_key_env` ; le traitement ne démarre pas |
| REQ-004 | Le profil est sélectionné par `--profile` > `$HDH_PROFILE` > `default_profile` du fichier > l'unique profil s'il n'y en a qu'un. Un profil inconnu est une **erreur**, jamais un repli sur le défaut | Given un fichier déclarant dev/preprod/prod, When `--profile preprd`, Then sortie en erreur (code 2) avec un message listant `dev, preprod, prod` et le fichier lu, sans aucun appel réseau |
| REQ-005 | La résolution est **champ par champ**, pas source par source : URL et clé se résolvent indépendamment | Given `--profile prod --api-key K`, When la résolution s'exécute, Then l'URL vient du profil et la clé vaut K. Given `--hdh-url U --profile prod`, Then l'URL vaut U et le nom de variable de clé vient du profil |
| REQ-006 | Rétrocompatibilité stricte : toute invocation existante conserve son comportement et son code de sortie | Given aucun fichier de configuration et aucune nouvelle variable d'environnement, When `push-hdh --hdh-url U` avec `$HDH_API_KEY` défini, Then comportement identique à avant. Given `--api-key-env MA_VAR`, Then la variable explicite gagne sur le profil et sur le défaut. Given aucune URL nulle part, Then code de sortie 2 (comme l'option requise aujourd'hui). Given aucune clé, Then code de sortie 1 (inchangé) |
| REQ-007 | La résolution est une fonction **pure**, sans I/O ni accès à `os.environ`, l'environnement et la configuration parsée lui étant injectés | Given un `env` fourni sous forme de dict et une configuration construite en mémoire, When la résolution est appelée, Then elle renvoie un résultat déterministe sans lire de fichier ni de variable d'environnement réelle (aucun `monkeypatch` requis dans les tests) |
| REQ-008 | L'état de poussée est cloisonné par instance dans un fichier unique versionné, la clé d'instance étant l'**URL de base normalisée** | Given un id enregistré pour l'instance A, When l'état est rouvert pour l'instance B, Then aucun id n'est visible et une poussée vers B crée le jeu au lieu de le mettre à jour. Given deux instances, Then le fichier contient `{"version": 2, "instances": {<url>: {<urn>: <id>}}}` |
| REQ-009 | Un fichier d'état au format plat existant est repris de façon transparente sous l'instance courante, **sans effet de bord à l'ouverture**, et signalé une seule fois | Given un fichier plat `{urn: id}`, When l'état est ouvert pour l'instance A, Then les ids sont visibles, un avertissement unique nomme A et le nombre d'ids repris, et le fichier sur disque reste **octet pour octet identique** tant qu'aucun `record()` n'a eu lieu (un `--dry-run` ne modifie rien). When un premier `record()` a lieu, Then le fichier est réécrit au format versionné |
| REQ-010 | Une **unique** fonction de normalisation d'URL alimente à la fois l'URL du client HTTP et la clé d'état, de sorte qu'ils ne puissent pas diverger | Given `https://Exemple.fr:443/api/`, When elle est normalisée, Then le résultat est `https://exemple.fr/api` et c'est cette valeur exacte que reçoivent `HdhClient(base_url=...)` et le compartiment d'état. Le `rstrip("/")` local de `cli.py:203` disparaît |
| REQ-011 | La suite de tests est hermétique à l'environnement du poste | Given un développeur ayant exporté `HDH_API_KEY` (ou `HDH_URL`, `HDH_PROFILE`, `HDH_CONFIG`), When `uv run pytest` s'exécute, Then les résultats sont identiques à ceux d'un environnement vierge |
| REQ-012 | L'**URI de base** (ADR-0005 §4, #136) est résolue par `--base-uri` > `base_uri` du profil sélectionné, pour `export-file` comme pour `push-hdh` (qui acceptent tous deux `--config`/`--profile`). **Aucune valeur par défaut** ; elle doit être une URI http(s) absolue, normalisée sans `/` final | Given un profil déclarant `base_uri: A`, When `--base-uri B`, Then B est utilisée. Given ni option ni `base_uri` dans le profil sélectionné, Then `ConfigError` qui indique comment la déclarer, code de sortie 2, sans aucun appel réseau. Given `base_uri: exemple.fr` dans un profil, Then le chargement du fichier échoue en nommant le profil |

### Nice-to-Have (P1)

| ID | Exigence | Critère d'acceptation |
|----|----------|------------------------|
| REQ-101 | `HdhClient` est couvert hors ligne (construction des 4 URLs, en-tête `X-API-Key`, traduction des statuts) via l'injection d'un `httpx.BaseTransport` | Given un `httpx.MockTransport`, When `create_dataset`/`update_dataset`/`whoami` sont appelées, Then la méthode, le chemin, les en-têtes et les paramètres attendus sont observés, et 401/404/500/erreur de transport produisent respectivement `HdhAuthError`/`HdhNotFoundError`/`HdhClientError`/`HdhTransportError`. `HdhClient` reste `frozen` |
| REQ-102 | `record()` relit-fusionne-écrit : il ne réécrit que son propre compartiment | Given deux processus poussant vers deux instances avec le même `--state-file`, When ils enregistrent chacun un id, Then les deux compartiments survivent |
| REQ-103 | Une mise à jour renvoyant 404 (id périmé) retombe sur une création et purge l'id obsolète | Given un id d'état absent de l'instance visée, When la poussée s'exécute, Then le jeu est créé et l'état corrigé, au lieu d'un `PushFailed` |

### Future Considerations (P2)

- Profils symétriques pour **DataHub** (source), raccordés à `from_config()`
  (`reader/graph.py:129`), avec le même fichier et la même précédence.
- Chemins/préfixe d'endpoints configurables par profil, si une instance n'expose
  pas `/ingest/datasets` à la racine.
- `--profile` sur `export-file` pour dériver `--base-uri` d'un profil.

## Success Metrics

**Leading indicators**
- Nombre d'informations à retaper pour une poussée vers une instance connue :
  de 1 URL complète + 1 clé à **1 nom de profil**.
- Couverture de la résolution de configuration : de 0 (aucun module) à la
  totalité des précédences de REQ-001/004/005 et des erreurs de REQ-002/003/004.
- Couverture de `PushState` : les 7 tests existants plus le cloisonnement et la
  migration (REQ-008/009).
- Secrets versionnables dans le fichier de configuration : **zéro par
  construction** (REQ-003).

**Lagging indicators**
- Absence de poussée vers la mauvaise instance signalée après mise en production
  (aujourd'hui non détectable autrement que par constat côté catalogue).
- Absence de doublon créé après un changement d'instance.

## Open Questions

- *Tranché le 2026-10-29 : les specs sont versionnées sous `docs/specs/`.*
  **`spec/` est gitignoré tout en restant suivi par git** (dernière ligne du
  `.gitignore`, ajoutée dans le lot en cours). Les specs restent-elles versionnées
  — auquel cas il faut retirer `spec/` du `.gitignore` ou faire un `git add -f` —
  ou deviennent-elles des documents de travail locaux ? À trancher avant de
  commiter ce PRD.
- **Nom des variables d'environnement** : `HDH_URL`, `HDH_PROFILE`, `HDH_CONFIG`
  retenus par cohérence avec `HDH_API_KEY` existante (décision « n'ajouter que du
  nouveau »). À confirmer, sachant que la doc parle désormais de « Catalogue de
  métadonnées » : le préfixe `HDH_` sera à reprendre dans le futur lot de
  renommage, avec la même mécanique d'alias.
- **REQ-101 dans ce lot ou en suivi ?** L'argument pour l'y inclure : ce lot rend
  `base_url` fourni par l'utilisateur puis normalisé par nous, donc « l'URL qu'on
  construit est bien celle qu'on appelle » devient un risque réel, aujourd'hui
  entièrement non testé (aucune occurrence de `httpx` dans `tests/`). L'argument
  contre : il exige un refactor de `hdh_client.py` (injection de transport) hors du
  périmètre « URL + auth ».

## Timeline Considerations

Aucune échéance contractuelle. Le lot P0 est cohérent et livrable d'un bloc, mais
se découpe naturellement en trois incréments indépendants convergeant sur le
câblage CLI : la résolution de configuration (REQ-001 à 007, 010, 011), le
cloisonnement de l'état (REQ-008, 009), puis le câblage de `push-hdh`. P1 et P2
sans dépendance bloquante.
