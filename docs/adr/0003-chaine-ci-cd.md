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
| `test` | matrice Python 3.10 / 3.11 / 3.12 ; `pytest` + `pytest-cov` → `coverage.xml` (upload Codecov depuis le leg 3.12) |
| `build` | `uv build` + fumée du wheel non-éditable (job existant, conservé) |
| `dependency-review` | `actions/dependency-review-action`, `fail-on-severity: high` + contrôle de licences, **bloquant** |

Config `ruff` : `select = [E, F, W, I, UP, B, SIM, C4, RUF, PL]`, `line-length = 100`,
`target-version = "py310"`, `per-file-ignores` (`tests/**` → `PLR2004`,
`**/__init__.py` → `F401`). Remplace flake8 + isort + black.

Config `mypy` : `strict = true`, `python_version = "3.10"`, périmètre
`src/dh_healthdcat` ; override `tests/**` (`disallow_untyped_defs = false`) ;
`ignore_missing_imports` par module pour `acryl-datahub` / `pyshacl` / `rdflib`.
CI uniquement (pas de hook pre-commit).

Outils de dev déplacés de `[project.optional-dependencies].dev` vers
`[dependency-groups].dev` (PEP 735, natif `uv`).

Le plafond de la matrice Python est calé sur la fourchette supportée par
`acryl-datahub` — à rouvrir quand la CLI DataHub monte à 3.13.

**Couverture** : pas de `--cov-fail-under`. La barrière est **Codecov** —
`project: auto` (anti-régression) et `patch: 80 %`, tous deux bloquants ;
`ignore: ["tests/**"]`.

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

## 2. Versioning et changelog : release-please

Mode **manifeste** (`release-please-config.json` +
`.release-please-manifest.json`), paquet racine `"."`, `release-type: python`,
`package-name: "dh-healthdcat"`, action `googleapis/release-please-action@v4`.

- `[project].version` de `pyproject.toml` reste **statique**, bumpé nativement
  (PEP 621). Pas de `__version__` dans le code ; pas de `extra-files`.
- `bootstrap-sha` figé au HEAD d'adoption → aucun changelog rétroactif.
- Pré-1.0 : `bump-minor-pre-major: true` (un breaking bumpe le minor, pas
  `1.0.0`), `bump-patch-for-minor-pre-major: false`. Passage à `1.0.0` =
  `release-as: "1.0.0"` manuel.
- Sections de changelog : **défaut de la stratégie `python`** accepté tel quel
  (`feat` / `fix` / `perf` / `deps` / `revert` / `docs` visibles ; `test` /
  `chore` / `build` / `ci` masqués → le bruit Dependabot et les `test:` restent
  hors changelog). Pas de clé `changelog-sections`.
- `include-component-in-tag: false` → tags `vX.Y.Z`.
- Option `signoff` activée (ADR-0002 §4).

## 3. Publication PyPI (`.github/workflows/release.yml`)

Un seul workflow, `on: push: branches: [main]`, `permissions: {}`,
`concurrency: { group: release, cancel-in-progress: false }`. Quatre jobs
enchaînés, tous gardés par
`if: needs.release-please.outputs.release_created == 'true'` :

`release-please` → `build` → `publish` → `smoke`.

- **Pas de PAT ni de GitHub App** : le tag posé par `GITHUB_TOKEN` ne déclenchant
  aucun workflow, le job `publish` vit dans le même workflow, gardé par la sortie
  `release_created` (et non par un trigger `on: release` ou `on: push: tags`).
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
`commit-message.prefix: "build"`, `cooldown.default-days: 3`,
`labels: [dependencies]`, `assignees: [davidouagne]`.

Auto-merge via `.github/workflows/dependabot-auto-merge.yml`
(`dependabot/fetch-metadata` + `gh pr merge --auto --merge`) : `semver-patch`
partout + `semver-minor` pour les seules dev-deps.

`uv.lock` est désormais **versionné** (retiré de `.gitignore`) — préalable à
l'écosystème `uv` de Dependabot, à `pip-audit`, et aux builds reproductibles.

Le drift des dépendances transitives est couvert par le `pip-audit`
hebdomadaire ; pas de `lockFileMaintenance`.

## 5. Sécurité

- `SECURITY.md` (FR, racine) : versions supportées = `main` + dernier tag ;
  signalement via le *private vulnerability reporting* GitHub ; pas de SLA
  (mainteneur unique).
- Fonctionnalités dépôt activées : private vulnerability reporting, secret
  scanning + push protection, Dependabot **alerts**. Dependabot *security
  updates* laissé **désactivé** (doublon avec §4).
- Chaque workflow déclare un `permissions:` explicite, minimal, par job.
  `default_workflow_permissions` du dépôt reste `read`.
- Épinglage des Actions : `@vN` (tag majeur), **sauf**
  `pypa/gh-action-pypi-publish` et les actions du job `publish` (dont
  `actions/download-artifact`), épinglées **par SHA** — exception au titre du
  privilège OIDC et de la publication de paquet.
- Hygiène des secrets : `config.py` refuse déjà toute `api_key` en clair dans le
  fichier de configuration versionnable (`api_key_env` uniquement) ; `.env` est
  gitignoré. Rien à corriger.
- Rulesets GitHub : `main` (voir *Conséquences*) et `v*` (création / suppression
  de tags restreintes, bypass `Repository admin` + `GitHub Actions`).
  Environnement `pypi` : *required reviewer* `davidouagne`,
  *deployment branches* = `main` (le job `publish` s'exécute dans le contexte
  `push`/`main`, pas sur une ref de tag).

**Hors périmètre** (à rouvrir seulement si l'ambition est redessinée, comme
effort neuf) : CodeQL / SAST, OpenSSF Scorecard, épinglage SHA généralisé,
provenance SLSA `actions/attest-build-provenance`. Les attestations PEP 740
natives de `gh-action-pypi-publish` restent, elles, dans le périmètre (§3).

## Conséquences

- **Dix checks requis** sur `main` : `lint`, `typecheck`, `test (3.10)`,
  `test (3.11)`, `test (3.12)`, `build`, `dco`, `commitlint`, `pr-title`,
  `dependency-review`. Un check n'est ajoutable au ruleset qu'après l'avoir vu
  tourner une fois → la mise en place est séquencée (voir l'issue de checklist
  d'implémentation liée à cet ADR).
- Ruleset `main` : PR obligatoire sans revue requise (0 approbation ; pas de
  `CODEOWNERS` — l'auto-merge Dependabot en dépend), `strict` / up-to-date
  désactivé, `Require conversation resolution` activé, force-push et suppression
  bloqués, `Require linear history` désactivé (ADR-0002 §1), bypass
  `Repository admin`.
- Fichiers à créer : `.github/workflows/{ci.yml (modifié), commit-policy.yml,
  audit.yml, release.yml, dependabot-auto-merge.yml}`, `.github/dependabot.yml`,
  `release-please-config.json`, `.release-please-manifest.json`, `SECURITY.md`,
  `codecov.yml`, `.pre-commit-config.yaml`, `.github/PULL_REQUEST_TEMPLATE.md` ;
  modifications de `pyproject.toml`, `.gitignore`, `CONTRIBUTING.md`, `README.md`.
