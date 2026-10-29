# Chaîne CI/CD : intégration continue, release automatisée, dépendances, sécurité

Status: accepted

Contexte : carte wayfinder [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17),
tickets [#18](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/18) (CI),
[#20](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/20) (sécurité),
[#24](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/24) (dépendances),
[#25](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/25) (release-please),
[#26](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/26) (publication PyPI).

Ambition retenue : « **standard Python complet** » — lint + typage + couverture +
audit en CI, publication PyPI automatisée — **sans** durcissement supply-chain
avancé. Modèle de référence : `davidouagne/sashimi`, dépassé côté versioning
(release-please) et publication (PyPI). Voir aussi ADR-0002 (politique de commits).

## 1. Intégration continue (`.github/workflows/ci.yml`)

Jobs parallèles, `permissions: {}` au niveau workflow, élévation minimale par job :

| Job | Contenu |
|---|---|
| `lint` | `ruff check` + `ruff format --check` ; puis `pip-audit` advisory (`continue-on-error`) |
| `typecheck` | `mypy` strict sur `src/dh_healthdcat` (`tests/` allégé) |
| `test` | matrice résolution × Python : `highest` (lock, maintenu au plus haut par Dependabot) sur 3.11 et 3.12, `lowest` (`--resolution lowest-direct`, planchers déclarés) sur 3.11 seulement *(3.10 retiré le 2026-10-26, fin de vie ; axe résolution ajouté le 2026-10-29, ADR-0004)* ; `pytest` + `pytest-cov` → `coverage.xml` (upload Codecov depuis `highest`/3.12) |
| `build` | `uv build` + fumée du wheel non-éditable (job existant, conservé) |

Axe de résolution (#127, ADR-0004 §3) : `lowest` vérifie que les planchers
déclarés dans `pyproject.toml` fonctionnent réellement (il a révélé
`typer>=0.12` faux face à `click` ≥ 8.2, relevé à `>=0.16`). Il ne croise que
Python 3.11 : la combinaison la plus ancienne de chaque axe est celle qui casse
la première, et doubler le leg ne couvrirait rien de plus. Les jobs portent
des noms `test (<résolution>, <python>)` ; le ruleset `main` n'exige que
l'agrégat `CI status`, qui dépend de tous les legs — aucune mise à jour du
ruleset n'est donc nécessaire quand la matrice change.

Pré-versions : aucun rc d'`acryl-datahub` n'entre dans le lock. La politique
par défaut d'uv (`if-necessary-or-explicit`) n'en retient une que si la
contrainte la nomme ou si aucune version stable ne la satisfait, et
Dependabot ne propose pas de pré-version tant que la version courante n'en est
pas une. `prerelease = "disallow"` a été écarté : il rétrogradait une
transitive (`mixpanel` 5.3 → 5.0, qui dépend d'une alpha `json-logic`) sans
rien ajouter pour `acryl-datahub`.

Dependabot : une montée `1.7.0.x → 1.7.0.y` est classée `semver-patch` par
`fetch-metadata` (vérifié sur #122, 1.7.0.16 → 1.7.0.17) et reste en
auto-merge ; l'élargissement `<1.8 → <1.9` est une mineure de dépendance de
production, donc en revue humaine (ADR-0004 §2).

`dependency-review` a été extrait dans son propre workflow,
`.github/workflows/dependency-review.yml` — voir §1bis — alignement sur
`datahub-yaml-source` ([#83](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/83)).

Config `ruff` : `select = [E, F, W, I, UP, B, SIM, C4, RUF, PL]`, `line-length = 100`,
`target-version = "py311"`, `per-file-ignores` (`tests/**` → `PLR2004`,
`**/__init__.py` → `F401`). Remplace flake8 + isort + black.

Config `mypy` : `strict = true`, `python_version = "3.11"`, périmètre
`src/dh_healthdcat` ; override `tests/**` (`disallow_untyped_defs = false`) ;
`ignore_missing_imports` par module pour `acryl-datahub` / `pyshacl` / `rdflib`.
CI uniquement (pas de hook pre-commit).

Outils de dev déplacés de `[project.optional-dependencies].dev` vers
`[dependency-groups].dev` (PEP 735, natif `uv`).

Le plafond de la matrice Python est calé sur la fourchette supportée par
`acryl-datahub` — à rouvrir quand la CLI DataHub monte à 3.13.

**Couverture** *(révisé par [#65](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/65) /
[#69](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/69), alignement sur
`datahub-yaml-source` ; seuil monté à 90% par
[#79](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/79))* :
la barrière réelle est `pytest --cov-fail-under=90` dans le job `test` (les
trois legs de la matrice). Codecov redevient **purement informatif** —
`project` et `patch` en `informational: true` dans `codecov.yml` (`patch`
aligné sur 90% par cohérence) — pour qu'une panne Codecov ou une PR de fork
sans jeton OIDC ne puisse plus faire échouer la CI. `ignore: ["tests/**"]`
inchangé. L'upload Codecov (`fail_ci_if_error: false`, `if: always()`) tente
toujours d'envoyer le rapport, y compris quand `pytest` a déjà fait échouer
le job sur la barrière de couverture.

**Audit** : `pip-audit` advisory à chaque PR + workflow dédié
`.github/workflows/audit.yml` (cron hebdomadaire lundi 06:00 UTC). Le job
`audit` reste **vert** tant que `pip-audit` s'exécute correctement ; une
vulnérabilité connue est un constat, pas un échec de CI, et ouvre une issue
`dependencies` dédoublonnée par titre (job `open-issue` conditionné au nombre
de vulnérabilités du rapport JSON, `issues: write` isolé). Le job ne rougit
que si `pip-audit` lui-même échoue (réseau, résolution, rapport illisible).

`.pre-commit-config.yaml` de base fourni (`ruff` en `language: system` via
`uv run` pour aligner les versions sur `uv.lock` ; `mypy` exclu), **non imposé**
en CI.

## 1bis. Revue de dépendances (`.github/workflows/dependency-review.yml`)

*(Extrait de `ci.yml` par [#83](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/83),
alignement sur `datahub-yaml-source`, qui l'a en workflow dédié plutôt qu'en
job de `ci.yml`.)* `actions/dependency-review-action`, `fail-on-severity: high`
+ contrôle de licences (refuse GPL/AGPL, incompatibles avec la licence
Apache-2.0 du dépôt), déclenché sur PR vers `main`. Le nom du job
(`dependency-review`) est inchangé — c'est lui, indépendamment du fichier qui
le porte, que référence le contexte requis dans le ruleset `main` (voir
*Conséquences*).

**Noms des workflows** *(alignés sur `datahub-yaml-source` par
[#83](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/83))* :
`audit.yml` (« Audit dependencies »), `commit-policy.yml` (« Commit policy »)
et `release.yml` (« Release ») portaient un `name:` différent du dépôt
jumeau ; `ci.yml` (« CI ») et `dependabot-auto-merge.yml` (« Dependabot
auto-merge ») étaient déjà alignés. Contenu des jobs inchangé.

## 2. Versioning et changelog : release-please

Mode **manifeste** (`release-please-config.json` +
`.release-please-manifest.json`), paquet racine `"."`, `release-type: python`,
`package-name: "dh-healthdcat"`, action `googleapis/release-please-action@v4`.

- `[project].version` de `pyproject.toml` reste **statique**, bumpé nativement
  (PEP 621). Pas de `__version__` dans le code ; pas de `extra-files`.
- `uv.lock` porte aussi la version du paquet racine (`[[package]]
  name = "dh-healthdcat"`), que release-please ne bumpe pas → décalage
  systématique à chaque release. Recalé par un step du job `release-please`
  (`uv lock` + commit `chore(main)` signé DCO sur la branche de la PR de
  release) plutôt que par un `extra-files` TOML fragile sur un fichier généré.
- `bootstrap-sha` figé au HEAD d'adoption → aucun changelog rétroactif.
- Pré-1.0 : `bump-minor-pre-major: true` (un breaking bumpe le minor, pas
  `1.0.0`), `bump-patch-for-minor-pre-major: false`. Passage à `1.0.0` =
  `release-as: "1.0.0"` manuel.
- Sections de changelog : **défaut de la stratégie `python`** accepté tel quel
  (`feat` / `fix` / `perf` / `deps` / `revert` / `docs` visibles ; `test` /
  `chore` / `build` / `ci` masqués → le bruit Dependabot et les `test:` restent
  hors changelog). Pas de clé `changelog-sections`.
- *Révisé le 2026-10-26* : les montées de dépendances de prod déclenchent une
  release patch. Le 2026-10-26, quatre PR Dependabot (dont `acryl-datahub`
  1.7.0.14 → 1.7.0.16) ont été fusionnées sans proposition de release : toutes
  en `build(deps)`, type masqué donc non releasable. Dependabot préfixe
  désormais les dépendances `uv` de prod en `deps` (visible, bump patch,
  section « Dependencies ») et garde `build` pour le dev et les GitHub
  Actions ; plus de `include: scope`, le type suffisant à distinguer. `deps`
  rejoint le `type-enum` (ADR-0002). Limite assumée : `pyproject.toml` ne
  porte que des planchers et `uv.lock` n'est pas dans le wheel, donc une
  telle release ne change pas ce qu'installe un utilisateur ; elle date et
  documente la version de DataHub contre laquelle la CI a validé l'exporter.
  Relever le plancher à chaque bump (`versioning-strategy: increase`) est
  écarté : il imposerait le dernier client DataHub, qui doit suivre la
  version du serveur de l'utilisateur.
- `include-component-in-tag: false` → tags `vX.Y.Z`.
- Option `signoff` activée (ADR-0002 §4).

## 3. Publication PyPI (`.github/workflows/release.yml`)

Un seul workflow, `on: push: branches: [main]` (+ `workflow_dispatch`),
`permissions: {}`, `concurrency: { group: release, cancel-in-progress: false }`.
Quatre jobs enchaînés, `build` → `publish` → `smoke` gardés par
`if: needs.release-please.outputs.release_created == 'true' || inputs.publish_tag` :

`release-please` → `build` → `publish` → `smoke`.

- **Pas de PAT ni de GitHub App** pour release-please (le PAT de l'auto-merge
  Dependabot, §4, sert seulement à ce que ses merges déclenchent ce workflow) :
  le tag posé par `GITHUB_TOKEN` ne déclenchant
  aucun workflow, le job `publish` vit dans le même workflow, gardé par la sortie
  `release_created` (et non par un trigger `on: release` ou `on: push: tags`).
- **Rattrapage** : `workflow_dispatch` avec input `publish_tag` (ex. `v0.1.3`)
  rejoue `build` → `publish` → `smoke` sur un tag déjà posé, pour le cas où le
  run automatique a échoué *après* le tag (job `release-please` rouge). Sans
  ce filet, une version tagguée mais non publiée n'a aucun chemin de reprise
  (`release_created` n'est vrai qu'au run qui crée la release).
- `build` (`contents: write`) : checkout du tag (`ref: tag_name`,
  `persist-credentials: false`), `uv build --no-sources`, `uvx twine check`,
  `gh release upload` des artefacts sur la Release créée par release-please,
  `upload-artifact`.
- `publish` (`id-token: write` seul, `environment: pypi`) : deux steps —
  `download-artifact` puis `pypa/gh-action-pypi-publish` via **Trusted
  Publishing** (OIDC, aucun token). `attestations: true` par défaut (PEP 740).
- `smoke` (`permissions: {}`, `continue-on-error: true`) : `pip install` depuis
  PyPI + `dh-healthdcat --help`, avec retry (propagation CDN). Advisory : une
  release publiée n'est pas annulable.
- Pas de TestPyPI.

Setup PyPI : *pending publisher* (`davidouagne` /
`datahub-healthdcat-ap-exporter` / `release.yml` / env `pypi`) — le projet
`dh-healthdcat` est créé automatiquement à la première publication.

## 4. Gestion des dépendances (`.github/dependabot.yml`)

**Dependabot** (pas Renovate — support `uv` natif depuis mars 2025, aucun manque
bloquant ; Renovate ne se justifierait que pour `lockFileMaintenance`
multi-dépôts). Écosystèmes `uv` et `github-actions` à la racine, hebdomadaire le
lundi, `open-pull-requests-limit: 5`.

Groupes : `dev-dependencies` (tout le dev en une PR), `prod-minor-patch`,
`actions` ; les majors de prod restent en PR individuelles à revue humaine.
`commit-message.prefix: "build"` *(révisé le 2026-10-26 : `deps` pour la prod
`uv`, voir §2)*, `cooldown.default-days: 3`,
`labels: [dependencies]`, `assignees: [davidouagne]`.

Auto-merge via `.github/workflows/dependabot-auto-merge.yml`
(`dependabot/fetch-metadata` + `gh pr merge --auto --rebase`, ADR-0002 §1) : `semver-patch`
partout + `semver-minor` pour les dev-deps et, *(révisé le 2026-10-13, #110)*,
pour les transitives (`dependency-type: indirect`, toujours des security
updates). *(Révisé le 2026-10-05, voir
Conséquences)* : `gh pr merge` s'authentifie avec le secret **Dependabot**
`AUTO_MERGE_TOKEN` (PAT fine-grained) plutôt qu'avec `GITHUB_TOKEN`, et le
déclencheur est borné à `pull_request: branches: [main]`.

`uv.lock` est désormais **versionné** (retiré de `.gitignore`) — préalable à
l'écosystème `uv` de Dependabot, à `pip-audit`, et aux builds reproductibles.

**Transitives** *(révisé après [#56](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/56) /
[#98](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/98))* :
les version updates ne touchent que les dépendances déclarées dans
`pyproject.toml`. Une transitive **vulnérable** est corrigée par les
Dependabot *security updates* (§5) ; le `pip-audit` hebdomadaire reste le
filet de détection, notamment quand le correctif est bloqué par la contrainte
d'un parent (Dependabot ne met pas à jour une transitive si cela exige de
monter le parent). Pas de `lockFileMaintenance` : les transitives non
vulnérables ne sont pas suivies.

## 5. Sécurité

- `SECURITY.md` (FR, racine) : versions supportées = `main` + dernier tag ;
  signalement via le *private vulnerability reporting* GitHub ; pas de SLA
  (mainteneur unique).
- Fonctionnalités dépôt activées : private vulnerability reporting, secret
  scanning + push protection, Dependabot **alerts** et Dependabot *security
  updates* *(activé après [#98](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/98),
  voir Conséquences)*.
- Chaque workflow déclare un `permissions:` explicite, minimal, par job.
  `default_workflow_permissions` du dépôt reste `read`.
- Épinglage des Actions : `@vN` (tag majeur), **sauf**
  `pypa/gh-action-pypi-publish` et les actions du job `publish` (dont
  `actions/download-artifact`), épinglées **par SHA** — exception au titre du
  privilège OIDC et de la publication de paquet.
- Hygiène des secrets : `config.py` refuse déjà toute `api_key` en clair dans le
  fichier de configuration versionnable (`api_key_env` uniquement) ; `.env` est
  gitignoré. Rien à corriger.
- Ruleset `main` (voir *Conséquences*) et ruleset `tags-v` (`refs/tags/v*` :
  suppression et mise à jour non fast-forward bloquées, pas de règle de
  création ; bypass `Repository admin` seul — `docs/rulesets/tags-v.json`).
  Environnement `pypi` : *required reviewer* `davidouagne`,
  *deployment branches* = `main` (le job `publish` s'exécute dans le contexte
  `push`/`main`, pas sur une ref de tag).
- CodeQL *default setup* activé
  ([#65](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/65) /
  [#68](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/68),
  alignement sur `datahub-yaml-source`) : `languages: [python, actions]`,
  `query_suite: default`, `threat_model: remote`, `schedule: weekly`. Non
  ajouté aux checks requis du ruleset `main` (traitement non
  bloquant, identique au dépôt jumeau).

**Hors périmètre** (à rouvrir seulement si l'ambition est redessinée, comme
effort neuf) : OpenSSF Scorecard, épinglage SHA généralisé, provenance SLSA
`actions/attest-build-provenance`. Les attestations PEP 740 natives de
`gh-action-pypi-publish` restent, elles, dans le périmètre (§3).

## Conséquences

- **Révisé par [#65](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/65) /
  [#67](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/67)**,
  alignement sur `datahub-yaml-source` : plutôt que dix checks individuels sur
  un ruleset, un job d'agrégation `CI status`
  ([#66](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/66))
  `needs: [lint, typecheck, test, build]` donne un seul contexte stable,
  insensible aux noms de legs de la matrice `test`.
- **Révisé par le passage de la protection classique au ruleset `main`** : après
  #67, `main` était protégé à la fois par la protection de branche classique
  (API `branches/{branch}/protection`) et par le ruleset `main` hérité de #27,
  qui exigeait encore les dix contextes individuels. Les deux s'appliquaient
  cumulativement et se contredisaient sur trois points (`dco` / `commitlint` /
  `pr-title` requis ou non, résolution des conversations, noms de legs de la
  matrice). La protection classique est **supprimée** ; le ruleset `main`
  (`docs/rulesets/main.json`) est l'unique protection de `main`, avec :
  PR obligatoire (0 approbation ; pas de `CODEOWNERS` — l'auto-merge Dependabot
  en dépend), `required_status_checks` = `CI status`, `dco`, `commitlint`,
  `pr-title`, `dependency-review` (`strict: false`), résolution des
  conversations **requise**, force-push (`non_fast_forward`) et suppression
  bloqués, bypass `Repository admin`. `Require linear history` reste désactivé
  (ADR-0002 §1). `CI status` n'agrège que `lint`, `typecheck`, `test` (toute la
  matrice) et `build` : les contrôles de politique de commits
  (`commit-policy.yml`, ADR-0002) et `dependency-review` restent des contextes
  distincts. Cette posture remplace celle décrite jusqu'ici (« pas un ruleset »,
  contextes `CI status` + `dependency-review` seuls). Le dépôt jumeau
  `datahub-yaml-source` porte la même configuration (ruleset seul, mêmes cinq
  contextes, protection classique absente) — vérifié en direct le 2026-09-20.
- **Révisé par le passage au merge par rebase** (2026-10-05, ADR-0002 §1) : le
  ruleset `main` n'autorise plus que le rebase (`allowed_merge_methods:
  ["rebase"]`), exige un historique linéaire (`required_linear_history`) et ne
  requiert plus le contexte `pr-title`. Contextes requis : `CI status`, `dco`,
  `commitlint`, `dependency-review`. La description ci-dessus (cinq contextes,
  `Require linear history` désactivé) est remplacée. Ce changement est propre à
  ce dépôt : `datahub-yaml-source` n'est pas modifié.
- **Révisé par l'activation des Dependabot *security updates*** (2026-10-05) :
  elles étaient laissées désactivées comme « doublon avec §4 ». Ce doublon
  n'existe que pour les dépendances directes : les version updates ignorent
  les transitives, et `pip-audit` détecte sans corriger. Cas observé : urllib3
  2.7.0, transitive vulnérable ([#98](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/98)),
  sans PR Dependabot alors que le correctif 2.8.0 était publié depuis le
  2026-09-15. Les security updates réutilisent `labels`, `commit-message` et
  `assignees` de `.github/dependabot.yml`, ignorent le `cooldown` et ne
  comptent pas dans `open-pull-requests-limit`. Leurs PR sur une transitive
  (`dependency-type: indirect`) ne sont pas auto-mergées et passent en revue
  humaine *(remplacé le 2026-10-13, voir ci-dessous)*. Limite connue : une transitive bloquée par la contrainte d'un parent
  (setuptools sous `acryl-datahub`,
  [#56](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/56))
  n'est pas corrigée ; seul le bump du parent par les version updates la règle.
- **Révisé par le passage de l'auto-merge Dependabot à un PAT** (2026-10-05,
  alignement sur `datahub-yaml-source`, son ADR-0006) : un merge programmé par
  `gh pr merge --auto` avec `GITHUB_TOKEN` est attribué à ce jeton, et GitHub ne
  déclenche aucun workflow sur les événements qu'il produit (hors
  `workflow_dispatch` / `repository_dispatch`). Le push sur `main` d'une PR
  Dependabot auto-mergée ne lançait donc ni `release.yml` (release-please ne
  mettait pas la PR de release à jour) ni `ci.yml`. Constaté sur le dépôt
  jumeau : deux bumps auto-mergés absents de sa PR de release jusqu'au push
  suivant. Désormais, `gh pr merge` utilise le secret **Dependabot**
  `AUTO_MERGE_TOKEN` (un workflow déclenché par Dependabot ne lit pas les
  secrets Actions) : PAT fine-grained limité à ce dépôt, permissions
  *Contents*, *Pull requests* et *Workflows* en lecture/écriture (*Workflows*
  car les PR Dependabot `github-actions` modifient `.github/workflows/`). Le
  merge est attribué au mainteneur et déclenche `release.yml` et `ci.yml`
  comme un merge manuel. Secret absent ou vide : avertissement et repli sur
  `GITHUB_TOKEN` (comportement antérieur). Le PAT expire : le renouveler avant
  échéance, sinon `gh pr merge` échoue et la PR attend un merge manuel. Le
  déclencheur est borné à `branches: [main]` pour que le PAT n'agisse que sous
  les checks requis du ruleset `main`. Alternatives écartées : `schedule`
  quotidien sur `release.yml` (PR de release en retard d'un jour, `ci.yml`
  toujours absent sur `main`), token de GitHub App (même effet, plus de pièces
  à maintenir pour un mainteneur unique). La règle « pas de PAT » du §3 vaut
  toujours pour release-please lui-même.
- **Révisé par l'auto-merge des security updates transitives** (2026-10-13,
  [#110](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/110)) :
  la PR #109 (multidict 6.7.1 → 6.9.1, correctif de GHSA-54p9-h82j-f925),
  `indirect` et `semver-minor`, est restée ouverte malgré des checks verts. Le
  job `auto-merge` affichait un succès alors que l'étape d'activation était
  sautée. Les montées patch et minor des transitives sont désormais
  auto-mergées. Les version updates ignorent les transitives, donc ces PR sont
  toujours des security updates. Justification : une vulnérabilité corrigée
  qui attend une revue reste ouverte, et `uv.lock` n'est pas inclus dans le
  wheel. Le bump ne touche donc que l'environnement de CI/dev, celui que les
  checks requis valident. Risque accepté : les security updates ignorent le
  `cooldown`, mais visent la version désignée par l'advisory et non la
  dernière publiée. Les majors et les montées minor des dépendances de prod
  directes restent en revue humaine (inchangé).
  Complément (2026-10-20, PR #113, aiohttp 3.14.3 → 3.14.4, patch) : sur une
  security update `indirect`, le message de commit de Dependabot ne porte que
  `dependency-version`, et `fetch-metadata` rend un `update-type` vide — même
  un patch n'était pas auto-mergé (cause probable de #101 et #109). Le
  workflow déduit alors le type de montée du titre « from X to Y » (deux
  premiers composants de version) ; un titre non reconnu reste en revue
  humaine, et un major déduit aussi.
- Fichiers à créer : `.github/workflows/{ci.yml (modifié), commit-policy.yml,
  audit.yml, release.yml, dependabot-auto-merge.yml}`, `.github/dependabot.yml`,
  `release-please-config.json`, `.release-please-manifest.json`, `SECURITY.md`,
  `codecov.yml`, `.pre-commit-config.yaml`, `.github/PULL_REQUEST_TEMPLATE.md` ;
  modifications de `pyproject.toml`, `.gitignore`, `CONTRIBUTING.md`, `README.md`.
