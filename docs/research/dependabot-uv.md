# Dependabot & `uv` : écosystème, groupes, auto-merge (état de l'art 2026)

Recherche pour la carte wayfinder #17, ticket #21. Sources primaires uniquement :
GitHub Docs (Dependabot), GitHub Changelog, docs Astral `uv`, `dependabot/fetch-metadata`.

Vérifié le 2026-08-28 contre les sources listées en fin de document.

## 1. Dependabot lit-il `uv.lock` / un `pyproject.toml` géré par `uv` ?

**Oui, nativement, via l'écosystème dédié `uv`.**

- `package-ecosystem` correct = **`"uv"`** (et **non** `"pip"`). C'est la valeur
  recommandée par Astral : « The package-ecosystem value for uv is `"uv"`. […]
  Dependabot supports updating `uv.lock` files. »
  Source : <https://docs.astral.sh/uv/guides/integration/dependabot/>
- Dependabot met à jour **à la fois `pyproject.toml` et `uv.lock`** (manifeste + lockfile),
  comme pour les autres écosystèmes à lockfile.
  Source : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>
- Chronologie (Changelog GitHub) :
  - **Version updates GA** le 2025-03-13 : « For projects that use `uv` as a package
    manager, Dependabot version updates can now ensure dependencies stay current. »
    <https://github.blog/changelog/2025-03-13-dependabot-version-updates-now-support-uv-in-general-availability/>
  - **Security updates** le 2025-12-16 : « Dependabot now supports security alerts and
    updates for uv. »
    <https://github.blog/changelog/2025-12-16-dependabot-security-updates-now-support-uv/>
- `uv` est traité au même rang que `pip` pour la catégorisation des dépendances : la
  clé `groups > dependency-type` est « Supported by: `bundler`, `composer`, `mix`,
  `maven`, `npm`, `pip`, `uv` ».
  Source : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>

### Limites connues (à surveiller)

- Astral signale que « there are some use cases that are not yet working » et renvoie au
  suivi <https://github.com/astral-sh/uv/issues/2512>.
  Source : <https://docs.astral.sh/uv/guides/integration/dependabot/>
- Si le projet fixe `exclude-newer` (cooldown côté `uv`), Astral recommande de poser un
  **cooldown Dependabot équivalent** (`cooldown:` / `default-days`, cf. §2) sinon la
  résolution `uv lock` échoue et la PR ne peut pas être produite.
  Source : <https://docs.astral.sh/uv/guides/integration/dependabot/>
- `versioning-strategy` pour `uv` : demande d'évolution ouverte
  (<https://github.com/dependabot/dependabot-core/issues/12162>, statut « Done » dans le
  board mais réponses mainteneurs non consultables) — vérifier le comportement `increase`
  contre l'`options reference` avant de s'y fier.

### Exemple minimal (`.github/dependabot.yml`)

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
```

Source : <https://docs.astral.sh/uv/guides/integration/dependabot/>

## 2. `groups` — regrouper les mises à jour dans une seule PR

Un bloc `groups` sous une entrée `updates` fusionne plusieurs bumps en **une PR par
groupe**. Clés (options reference) :

| Clé | Valeurs | Rôle |
|-----|---------|------|
| `applies-to` | `version-updates` (défaut) \| `security-updates` | à quel type de MAJ le groupe s'applique |
| `dependency-type` | `development` \| `production` | filtre dev vs prod (supporté par `uv`) ; par défaut tous types |
| `patterns` | liste, `*` en joker | noms de dépendances à inclure |
| `exclude-patterns` | liste, `*` en joker | noms à exclure |
| `update-types` | `major` \| `minor` \| `patch` (liste) | limite le groupe à certains niveaux semver ; par défaut tous |

Source : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>

Exemple — un groupe « toutes les dépendances de dev » + un groupe « patchs prod » :

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      dev-dependencies:
        dependency-type: "development"
        patterns: ["*"]
      prod-patches:
        dependency-type: "production"
        update-types: ["patch"]
```

Note 2026 : le regroupement fonctionne aussi **au travers de plusieurs écosystèmes**
(« Single pull request for Dependabot / multi-ecosystem », GA 2025-07-01,
<https://github.blog/changelog/2025-07-01-single-pull-request-for-dependabot-multi-ecosystem-support/>)
et **par nom de dépendance à travers plusieurs répertoires**
(<https://github.blog/changelog/2026-02-24-dependabot-can-group-updates-by-dependency-name-across-multiple-directories/>).

Cooldown : la clé `cooldown` (avec `default-days`, `semver-major-days`,
`semver-minor-days`, `semver-patch-days`) est disponible et **supportée pour `uv`**.
Source : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>

## 3. Auto-merge : `dependabot/fetch-metadata` + `gh pr merge --auto`

Mécanisme recommandé par GitHub : un workflow déclenché `on: pull_request`, filtré sur
l'auteur `dependabot[bot]`, qui récupère les métadonnées de la PR puis active
l'auto-merge natif de GitHub.

```yaml
name: Dependabot auto-merge
on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot:
    runs-on: ubuntu-latest
    if: github.event.pull_request.user.login == 'dependabot[bot]'
    steps:
      - name: Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@<pin-sha>
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"
      - name: Enable auto-merge for Dependabot PRs
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: gh pr merge --auto --merge "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Source : <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>

Sorties utiles de `fetch-metadata` pour les conditions :
`update-type` (`version-update:semver-patch|minor|major`), `dependency-type`
(`direct:production`, `direct:development`, `indirect`), `dependency-names`.
Source : <https://github.com/dependabot/fetch-metadata>

### Interaction avec la protection de branche

- `gh pr merge --auto` **ne contourne rien** : GitHub ne fusionne que lorsque **toutes
  les conditions de la branche protégée sont vertes** (checks requis, revues requises,
  conversations résolues…). Il faut donc activer « Allow auto-merge » sur le dépôt et
  « Require status checks to pass before merging » sur la branche cible.
  Source : <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>
- **`GITHUB_TOKEN` est en lecture seule** pour les runs déclenchés par Dependabot sur les
  événements `pull_request`, `push`, etc. On regagne les droits d'écriture nécessaires en
  déclarant explicitement `permissions:` dans le workflow (`pull-requests: write` pour
  approuver, `contents: write` pour mer.).
  Source : <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>
- Si la branche **exige N approbations**, ajouter une étape
  `gh pr review --approve "$PR_URL"` (avec `pull-requests: write`). Attention : une revue
  faite avec `GITHUB_TOKEN` (compte `github-actions[bot]`) **ne satisfait pas** une règle
  CODEOWNERS ni « Require review from Code Owners » — il faut alors un PAT / GitHub App,
  ou exempter Dependabot, ou retirer l'exigence de revue sur ces PR.
- Si la branche cible utilise une **merge queue**, `GITHUB_TOKEN` ne peut pas ajouter la
  PR à la file : PAT ou token GitHub App avec droit de merge requis.
  Source : <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>
- Les secrets/vars de la PR sont ceux du contexte **Dependabot** (`Settings > Secrets >
  Dependabot`), pas ceux d'Actions, pour les runs déclenchés par Dependabot.

## 4. Écosystème `github-actions` — `directory` et nouveautés 2026

- Valeur `directory` : **`"/"`**. « Dependabot will search the `/.github/workflows`
  directory, as well as the `action.yml`/`action.yaml` file from the root directory. »
  Source : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>
- Clé plurielle **`directories`** (liste ; supporte `*` et le globbing, contrairement à
  `directory`) disponible depuis 2024-06-25 — utile pour des actions composites dans des
  sous-dossiers.
  Source : <https://github.blog/changelog/2024-06-25-simplified-dependabot-yml-configuration-with-multi-directory-key-directories-and-wildcard-glob-support/>
- Nouveauté 2026-02-24 : regroupement des updates **par nom de dépendance à travers
  plusieurs répertoires** (réduit le nombre de PR quand la même action est épinglée à
  plusieurs endroits).
  Source : <https://github.blog/changelog/2026-02-24-dependabot-can-group-updates-by-dependency-name-across-multiple-directories/>
- Bonnes pratiques inchangées : épingler les actions au SHA, et grouper les bumps
  `github-actions` (souvent bruyants) via un `groups: { actions: { patterns: ["*"] } }`.

```yaml
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      actions:
        patterns: ["*"]
```

## 5. Alternative Renovate (pour un dépôt `uv`)

Renovate (app tierce Mend, ou self-hosted) apporte, au-delà de Dependabot : une détection
`uv` native via le manager **`pep621`** (met à jour `pyproject.toml` **et** `uv.lock`, y
compris `tool.uv.dev-dependencies` / `tool.uv.sources` et les uv workspaces —
<https://docs.renovatebot.com/modules/manager/pep621/>), le **`lockFileMaintenance`** qui
rafraîchit périodiquement tout le lockfile pour capter les transitives
(`{"lockFileMaintenance": {"enabled": true}}`, recommandé par Astral —
<https://docs.astral.sh/uv/guides/integration/renovate/>), un large jeu de **presets**
partageables (`config:recommended`, `schedule:*`, `group:*`, dependency dashboard,
`minimumReleaseAge` équivalent au cooldown), et un contrôle de regroupement /
`packageRules` nettement plus fin. Le coût : c'est une **application tierce** à installer
et à autoriser sur l'org (revue sécurité, permissions dépôt étendues), une courbe de
configuration plus raide, et pour `uv.lock` des rugosités documentées (index PyPI privé
non transmis à `uv lock --upgrade`, contamination de `lockedVersion` entre `pyproject.toml`
— discussions renovatebot/renovate #40201, #41719). Dependabot reste « zéro install,
intégré GitHub » ; Renovate se justifie si l'on veut le lockFileMaintenance des
transitives et le partage de presets à l'échelle de plusieurs dépôts.

## Recommandation

1. Ajouter une entrée `package-ecosystem: "uv"`, `directory: "/"`, `schedule.interval:
   "weekly"` dans `.github/dependabot.yml` — Dependabot mettra à jour `pyproject.toml` et
   `uv.lock`. Garder l'entrée `github-actions` existante avec `directory: "/"`.
2. Grouper : un groupe `dev-dependencies` (`dependency-type: development`, `patterns:
   ["*"]`), un groupe `prod-minor-patch` (`update-types: ["minor","patch"]`), un groupe
   `actions` pour `github-actions`. Laisser les `major` en PR individuelles.
3. Auto-merge via un workflow `dependabot/fetch-metadata` + `gh pr merge --auto --merge`,
   limité à `update-type == version-update:semver-patch` (voire `semver-minor` pour les
   dev-deps), avec `permissions: { contents: write, pull-requests: write }`. Activer
   « Allow auto-merge » + checks requis sur `main` ; ne pas exiger de revue humaine /
   CODEOWNERS sur les PR Dependabot (sinon prévoir une étape `gh pr review --approve`, qui
   ne satisfait pas CODEOWNERS avec `GITHUB_TOKEN`).
4. Si le projet adopte `exclude-newer`, ajouter un `cooldown` Dependabot cohérent.
5. Rester sur Dependabot (intégré, zéro install). N'envisager Renovate que si le besoin de
   `lockFileMaintenance` (transitives) ou de presets multi-dépôts devient concret.

## Sources

- Astral — Using uv with Dependabot : <https://docs.astral.sh/uv/guides/integration/dependabot/>
- Astral — Using uv with Renovate : <https://docs.astral.sh/uv/guides/integration/renovate/>
- GitHub Docs — Dependabot options reference : <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>
- GitHub Docs — Automating Dependabot with GitHub Actions : <https://docs.github.com/en/code-security/dependabot/working-with-dependabot/automating-dependabot-with-github-actions>
- GitHub Docs — Dependabot supported ecosystems : <https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories>
- GitHub — `dependabot/fetch-metadata` : <https://github.com/dependabot/fetch-metadata>
- Changelog — Dependabot version updates support uv (GA, 2025-03-13) : <https://github.blog/changelog/2025-03-13-dependabot-version-updates-now-support-uv-in-general-availability/>
- Changelog — Dependabot security updates support uv (2025-12-16) : <https://github.blog/changelog/2025-12-16-dependabot-security-updates-now-support-uv/>
- Changelog — Single PR for Dependabot / multi-ecosystem (2025-07-01) : <https://github.blog/changelog/2025-07-01-single-pull-request-for-dependabot-multi-ecosystem-support/>
- Changelog — `directories` key + glob (2024-06-25) : <https://github.blog/changelog/2024-06-25-simplified-dependabot-yml-configuration-with-multi-directory-key-directories-and-wildcard-glob-support/>
- Changelog — Group updates by dependency name across directories (2026-02-24) : <https://github.blog/changelog/2026-02-24-dependabot-can-group-updates-by-dependency-name-across-multiple-directories/>
- Renovate Docs — PEP 621 manager (uv, `lockFileMaintenance`) : <https://docs.renovatebot.com/modules/manager/pep621/>
- dependabot/dependabot-core#12162 — `versioning-strategy` pour uv : <https://github.com/dependabot/dependabot-core/issues/12162>
- astral-sh/uv#2512 — suivi compatibilité Dependabot : <https://github.com/astral-sh/uv/issues/2512>
