# release-please pour un paquet Python + publication PyPI (Trusted Publishing)

Recherche préalable aux tickets « Configuration release-please » (#25) et
« Topologie du workflow de release ». Objet : fixer, **depuis les sources primaires**,
le patron 2026 pour automatiser les releases de `dh-healthdcat` (paquet unique,
`src/dh_healthdcat/`, build-backend `hatchling`, `[project].version` statique) et
chaîner une publication PyPI sans jeton long-lived.

Vérifié le 2026-08-28 contre les sources primaires listées en fin de document
(release-please `17.11.2`, `googleapis/release-please-action@v4`).

## 1. Action et version courantes

- **`googleapis/release-please-action@v4`**. Le dépôt de l'action est
  `googleapis/release-please-action` (l'ancien `google-github-actions/release-please-action`
  n'est plus le canonique). Runtime `node24`.
  Source : <https://github.com/googleapis/release-please-action/blob/main/action.yml>,
  <https://github.com/googleapis/release-please-action/blob/main/README.md>.
- CLI/bibliothèque sous-jacente : `googleapis/release-please`, version `17.11.2`
  au 2026-08-28 (`package.json`).
  Source : <https://github.com/googleapis/release-please/blob/main/package.json>.
- **v4 est « manifest-first »** : si `release-type` n'est **pas** renseigné, l'action
  lit une configuration manifeste (`release-please-config.json` +
  `.release-please-manifest.json`). Toute configuration avancée passe désormais
  obligatoirement par ces fichiers ; les anciennes entrées d'action (`changelog-types`,
  `extra-files`, `bump-minor-pre-major`, …) ont été retirées au profit des clés du
  fichier de config.
  Source : README §« Advanced Release Configuration » et §« Upgrading from v3 to v4 »
  <https://github.com/googleapis/release-please-action/blob/main/README.md>.

## 2. `release-type: python` — ce qu'il bumpe exactement

Stratégie `Python` : `src/strategies/python.ts`. À chaque release, elle produit les
`Update` suivants (tous en `createIfMissing: false`, sauf le CHANGELOG) :
Source : <https://github.com/googleapis/release-please/blob/main/src/strategies/python.ts>.

| Fichier | Comportement |
|---|---|
| `CHANGELOG.md` | créé si absent |
| `setup.cfg` | mis à jour **si présent** |
| `setup.py` | mis à jour **si présent** |
| `pyproject.toml` | mis à jour **si présent et versionné** (voir ci-dessous) |
| `<name>/__init__.py`, `src/<name>/__init__.py`, idem avec `-`→`_` | ligne `__version__` remplacée **si le fichier et la ligne existent** |
| tout `version.py` trouvé dans le repo (recherche par nom de fichier) | ligne `__version__` remplacée |
| `changelog.json` | mis à jour **si présent** |

### `pyproject.toml` : support natif de `[project].version` (PEP 621)

`src/updaters/python/pyproject-toml.ts` lit `parsed.project || parsed.tool?.poetry`
et réécrit la clé `version` sous `[project]` (PEP 621) **ou**, à défaut, sous
`[tool.poetry]`. Donc :

- `[project].version = "x.y.z"` **statique** → supporté **nativement**, aucun
  `extra-files` ni plugin nécessaire. C'est le cas de `dh-healthdcat` aujourd'hui.
- Si `version` est dans `[project].dynamic` (version calculée, p. ex. `hatch-vcs`/
  `setuptools-scm`), l'updater **loggue un warning et ne touche pas au fichier**
  (« dynamic version found in 'pyproject.toml'. Skipping update. »). Dans ce cas la
  source de vérité reste le tag Git ; release-please ne pilote plus la version dans
  `pyproject.toml`.
- `pyproject.toml` sans clé `version` du tout et sans `dynamic` → l'updater lève
  `Error('invalid file')`.

Source : <https://github.com/googleapis/release-please/blob/main/src/updaters/python/pyproject-toml.ts>.

### `__version__` dans `src/dh_healthdcat/__init__.py`

Updater `PythonFileWithVersion` : simple remplacement par regex

```
/(__version__ ?= ?["'])[0-9]+\.[0-9]+\.[0-9]+(?:-\w+)?(["'])/
```

Source : <https://github.com/googleapis/release-please/blob/main/src/updaters/python/python-file-with-version.ts>.

Conséquences pour ce repo :

- Le nom de paquet `[project].name = "dh-healthdcat"` : la stratégie teste
  `dh-healthdcat/…` **et** `dh_healthdcat/…` (substitution `-`→`_`), préfixés ou non
  par `src/`. Donc `src/dh_healthdcat/__init__.py` **est bien dans la liste des
  cibles** — pas de config supplémentaire à prévoir pour l'y inclure.
- **Mais** `createIfMissing: false` + regex exigeant une ligne déjà présente : le
  `src/dh_healthdcat/__init__.py` **actuellement vide** ne sera pas modifié tant
  qu'on n'y ajoute pas manuellement une première ligne `__version__ = "0.1.0"`
  (format semver strict, guillemets simples ou doubles). Sans cette ligne, la mise à
  jour est silencieusement ignorée — pas d'erreur.
- Il n'y a **pas** de mécanisme « ajouter le `__version__` s'il n'existe pas ».

### Alternative générique : `extra-files`

Pour tout fichier non couvert (ou pour forcer un chemin), la config manifeste accepte
`extra-files` avec des updaters typés. Pour du TOML :

```json
{
  "extra-files": [
    { "type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version" }
  ]
}
```

Types disponibles : `json` / `yaml` / `toml` (via `jsonpath`), `xml` (via `xpath`),
et le « Generic updater » (annotations `x-release-please-version` /
`x-release-please-start-version` … `x-release-please-end` dans le fichier).
Pour `dh-healthdcat`, `extra-files` **n'est pas nécessaire** : `[project].version`
statique est déjà géré nativement.
Source : <https://github.com/googleapis/release-please/blob/main/docs/customizing.md> (§ Updating arbitrary files).

### Version initiale

`initialReleaseVersion()` de la stratégie Python = `0.1.0` (surchargée par
`initial-version` / `release-as` au besoin).
Source : `src/strategies/python.ts`.

## 3. Mode `manifest` vs config simple (repo mono-paquet)

- **Config « simple » (`release-type: python` seul, sans fichiers)** : possible,
  « the most straight-forward configuration option, but allows for **no further
  customization** » (README). Aucun `changelog-sections`, aucun `extra-files`,
  aucun réglage fin.
- **Mode manifeste** : deux fichiers versionnés — `release-please-config.json`
  (config) et `.release-please-manifest.json` (versions courantes, `{}` au
  bootstrap). Le paquet racine se déclare avec le chemin spécial `"."`.
  « originally designed for repositories that contain multiple releasable
  artifacts [...] also supports single artifact workflows just as easily. »
  Source : <https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md>.

Exemple minimal pour `dh-healthdcat` (`release-please-config.json`) :

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    ".": {
      "release-type": "python",
      "package-name": "dh-healthdcat"
    }
  }
}
```

et `.release-please-manifest.json` :

```json
{ ".": "0.1.0" }
```

**Recommandation : mode manifeste**, même pour un paquet unique. Motifs : c'est le
mode par défaut de l'action v4, le seul qui donne accès à `changelog-sections` /
`extra-files` / `bootstrap-sha` / `initial-version`, il fige la config en revue de
code, et il évite une réécriture le jour où un 2ᵉ artefact apparaît. Aucune source
primaire ne déclare le mode non-manifeste « déprécié », mais toute la doc avancée et
le README v4 sont écrits pour le manifeste.

## 4. Sections CHANGELOG : mapping des types Conventional Commits

**Important** : la stratégie Python définit **son propre défaut**
`CHANGELOG_SECTIONS`, différent du défaut global de release-please
(`src/strategies/python.ts`) :

| type | section | visible ? |
|---|---|---|
| `feat` | Features | oui |
| `fix` | Bug Fixes | oui |
| `perf` | Performance Improvements | oui |
| `deps` | Dependencies | oui |
| `revert` | Reverts | oui |
| `docs` | Documentation | **oui** (visible pour la stratégie Python) |
| `style` | Styles | `hidden: true` |
| `chore` | Miscellaneous Chores | `hidden: true` |
| `refactor` | Code Refactoring | `hidden: true` |
| `test` | Tests | `hidden: true` |
| `build` | Build System | `hidden: true` |
| `ci` | Continuous Integration | `hidden: true` |

Pour mémoire, le **défaut global** (preset `conventional-changelog-conventionalcommits`
`^6.0.0`, épinglé par release-please) masque en plus `docs` et ne connaît pas `deps` :
`feat`/`feature`→Features, `fix`→Bug Fixes, `perf`→Performance Improvements,
`revert`→Reverts, puis `docs`/`style`/`chore`/`refactor`/`test`/`build`/`ci` tous
`hidden: true`.
Sources : <https://github.com/googleapis/release-please/blob/main/src/strategies/python.ts>,
<https://github.com/conventional-changelog/conventional-changelog/blob/master/packages/conventional-changelog-conventionalcommits/src/constants.js>,
<https://github.com/googleapis/release-please/blob/main/src/changelog-notes/default.ts>.

### Réponses à la question posée (`feat`, `fix`, `test`, `docs`, `chore`)

Avec `release-type: python` et **sans** override :

- `feat` → section **Features**, visible ; bump **minor**.
- `fix` → section **Bug Fixes**, visible ; bump **patch**.
- `docs` → section **Documentation**, **visible** (spécificité Python) ; **pas de bump**.
- `test` → section **Tests**, **masquée** ; pas de bump.
- `chore` → section **Miscellaneous Chores**, **masquée** ; pas de bump.
- `feat!` / `fix!` / `<type>!` ou pied de commit `BREAKING CHANGE:` → bump **major**
  (pré-1.0 : `bump-minor-pre-major` / `bump-patch-for-minor-pre-major` modulent).
  Source : README §« How should I write my commits? »
  <https://github.com/googleapis/release-please-action/blob/main/README.md>.

### Override via `changelog-sections`

Clé `changelog-sections` dans `release-please-config.json` (racine ou par-paquet).
Le tableau fourni **remplace intégralement** la liste des types (il n'est pas
fusionné avec le défaut : dans `src/changelog-notes/default.ts`, `config.types =
options.changelogSections`). Il faut donc **re-lister tous les types voulus**, y
compris `feat`/`fix`. Exemple pour rendre `test` visible et garder le reste du défaut
Python :

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "package-name": "dh-healthdcat",
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance Improvements" },
        { "type": "deps", "section": "Dependencies" },
        { "type": "revert", "section": "Reverts" },
        { "type": "docs", "section": "Documentation" },
        { "type": "test", "section": "Tests" },
        { "type": "refactor", "section": "Code Refactoring", "hidden": true },
        { "type": "style", "section": "Styles", "hidden": true },
        { "type": "chore", "section": "Miscellaneous Chores", "hidden": true },
        { "type": "build", "section": "Build System", "hidden": true },
        { "type": "ci", "section": "Continuous Integration", "hidden": true }
      ]
    }
  }
}
```

Note : le mapping type→bump (`feat`=minor, `fix`=patch, `!`=major) est **indépendant**
de `changelog-sections` ; renommer/masquer une section ne change pas le calcul de
version. (Un `chore:` ne bumpe pas — cf. `googleapis/release-please#2638`.)
Source : <https://github.com/googleapis/release-please/blob/main/docs/customizing.md>.

## 5. Chaînage : release-please → build/publish PyPI

### Le piège central (`GITHUB_TOKEN`)

À la fusion de la Release PR, release-please crée le **tag** et la **GitHub Release**
via l'API, authentifié avec le token de l'action. Si ce token est le `GITHUB_TOKEN`
par défaut :

> « all resources created by `release-please` (release tag or release pull request)
> **will not trigger future GitHub actions workflows**, and workflows normally
> triggered by `release.created` events **will also not run**. »
> — README release-please-action, §« Other Actions on Release Please PRs ».

C'est la règle GitHub générale :

> « When you use the repository's `GITHUB_TOKEN` to perform tasks, events triggered
> by the `GITHUB_TOKEN` will not create a new workflow run [...] with the following
> exceptions » — seuls `workflow_dispatch` et `repository_dispatch` (et
> `pull_request` `opened`/`synchronize`/`reopened`, mais en état « approval
> required ») échappent à la règle.
> Source : <https://docs.github.com/en/actions/concepts/security/github_token>
> (« GITHUB_TOKEN »), introduit le 2022-09-08
> <https://github.blog/changelog/2022-09-08-github-actions-use-github_token-with-workflow_dispatch-and-repository_dispatch/>.

Donc **`on: release: [published]` ET `on: push: tags:` sont tous deux inertes** si
release-please tourne avec le `GITHUB_TOKEN`. Choisir entre ces deux triggers ne
règle rien ; il faut lever le blocage à la source.

### Contournements (par ordre de préférence pour un repo mono-paquet)

1. **Publier dans le même workflow, étape gardée par `release_created`** (patron
   recommandé par le README de l'action, exemple `npm publish` transposé) :

   ```yaml
   name: release-please
   on:
     push:
       branches: [main]
   permissions:
     contents: write
     issues: write
     pull-requests: write
   jobs:
     release-please:
       runs-on: ubuntu-latest
       outputs:
         release_created: ${{ steps.release.outputs.release_created }}
         tag_name: ${{ steps.release.outputs.tag_name }}
       steps:
         - uses: googleapis/release-please-action@v4
           id: release
           with:
             config-file: release-please-config.json
             manifest-file: .release-please-manifest.json
     publish:
       needs: release-please
       if: ${{ needs.release-please.outputs.release_created == 'true' }}
       runs-on: ubuntu-latest
       environment: pypi
       permissions:
         id-token: write            # OIDC / PyPI Trusted Publishing
       steps:
         - uses: actions/checkout@v4
           with:
             ref: ${{ needs.release-please.outputs.tag_name }}
         - uses: actions/setup-python@v5
           with:
             python-version: "3.x"
         - run: python -m pip install -U build
         - run: python -m build
         - uses: pypa/gh-action-pypi-publish@release/v1
   ```

   Sorties utiles : `release_created` (composant racine), `releases_created`,
   `tag_name`, `version`, `sha`, `paths_released`. En mode multi-paquets les sorties
   sont préfixées `"<path>--release_created"`, etc.
   Source : README §Outputs
   <https://github.com/googleapis/release-please-action/blob/main/README.md>.

   Avantages : pas de second token, pas de piège de trigger, checkout garanti sur le
   bon tag via `tag_name`. Inconvénient : le job publish vit dans le workflow
   « release-please » plutôt que dans un workflow dédié `on: release`.

2. **Faire tourner release-please avec un token qui déclenche les workflows**
   (Personal Access Token à portée fine, ou token d'installation d'une GitHub App —
   p. ex. `actions/create-github-app-token`). Le tag/Release étant alors créés sous
   une autre identité, un workflow séparé `on: release: types: [published]` ou
   `on: push: tags: ['v*']` se déclenche normalement. C'est aussi ce qu'il faut pour
   que la **CI s'exécute sur la Release PR elle-même**.
   Source : README §« GitHub Credentials » / §« Other Actions on Release Please PRs ».

3. **`workflow_dispatch` / `repository_dispatch` explicite** depuis le job
   release-please (ces deux events déclenchent même via `GITHUB_TOKEN`). Plus de
   pièces mobiles ; utile si le publish doit rester un workflow autonome sans PAT.

### Côté PyPI : Trusted Publishing (OIDC), pas de token long-lived

- Trusted Publishing échange un jeton OIDC éphémère (≤ 15 min) contre un token
  d'upload ; « trusted publishing is now encouraged over API tokens as a best
  practice ». GitHub Actions est un fournisseur OIDC supporté.
  Sources : <https://docs.pypi.org/trusted-publishers/>,
  <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/README.md>.
- Le job qui publie doit avoir **`permissions: id-token: write`** (mandatory),
  posé **au niveau du job** et non du workflow (« only set the `id-token: write`
  permission in the job that does the publishing »).
  Source : <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/README.md>.
- Utiliser **`pypa/gh-action-pypi-publish@release/v1`** (la branche `master` est
  sunset ; épingler `release/v1` ou un SHA). Ne passer **ni `user` ni `password`**
  pour rester en flux OIDC. L'action ne construit pas les dists : `python -m build`
  en amont, artefacts dans `dist/`.
  Source : idem, §« Trusted Publishing » et §« Non-goals ».
- **GitHub Environment** (`environment: pypi`) « optional, but strongly encouraged » —
  permet règles de protection + scoping du Trusted Publisher côté PyPI.
  Source : <https://docs.pypi.org/trusted-publishers/using-a-publisher/>.
- Exemple canonique PyPI : trigger `on: release: types: [published]` (valable
  **uniquement** si la Release est créée par une identité ≠ `GITHUB_TOKEN`, cf.
  contournement 2). Sinon, préférer le contournement 1.
  Source : <https://docs.pypi.org/trusted-publishers/using-a-publisher/>.

## 6. Permissions requises

### Job release-please (`googleapis/release-please-action@v4`)

```yaml
permissions:
  contents: write         # créer commits/branche de la Release PR, tag, GitHub Release
  pull-requests: write    # ouvrir/mettre à jour la Release PR
  issues: write           # labels (déclaré requis par le README ; sinon skip-labeling: true)
```

Plus, côté repo : Settings → Actions → General → « Allow GitHub Actions to create and
approve pull requests ».
Source : README §« Workflow Permissions »
<https://github.com/googleapis/release-please-action/blob/main/README.md>.

### Job publish PyPI

```yaml
permissions:
  id-token: write         # obligatoire pour Trusted Publishing (OIDC)
  contents: read          # checkout du tag
```

Source : <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/README.md>,
<https://docs.pypi.org/trusted-publishers/using-a-publisher/>.

## Recommendation

1. **Mode manifeste** (`release-please-config.json` + `.release-please-manifest.json`),
   paquet racine `"."`, `release-type: python`, `package-name: "dh-healthdcat"`.
   C'est le défaut de l'action v4 et le seul mode donnant accès à `changelog-sections`.
2. **Garder `[project].version` statique dans `pyproject.toml`** : release-please le
   bumpe nativement (PEP 621), rien à configurer. Ne pas passer la version en
   `dynamic` (sinon release-please cesse de la piloter). `setup.py`/`setup.cfg`
   absents → non concernés.
3. **`__version__`** : si on veut qu'il soit synchronisé, ajouter **une fois**
   `__version__ = "0.1.0"` dans `src/dh_healthdcat/__init__.py` (aujourd'hui vide) ;
   ce chemin est déjà dans les cibles de la stratégie Python (nom `dh-healthdcat` →
   `dh_healthdcat`). Sinon, laisser le fichier vide et exposer la version via
   `importlib.metadata.version("dh-healthdcat")` — dans ce cas ne rien ajouter.
4. **CHANGELOG** : le défaut de la stratégie Python suffit (`feat`/`fix`/`perf`/
   `deps`/`revert`/`docs` visibles ; `test`/`chore`/`refactor`/`style`/`build`/`ci`
   masqués). N'ajouter `changelog-sections` que si l'on veut dévoiler `test`/`chore` —
   et alors **re-lister tous les types** (le tableau remplace le défaut).
5. **Chaînage** : un seul workflow `on: push: branches: [main]`, job `release-please`
   puis job `publish` avec `needs:` + `if: needs.release-please.outputs.release_created
   == 'true'`, checkout sur `outputs.tag_name`. Éviter de dépendre d'un trigger
   `on: release`/`on: push: tags` tant que release-please tourne sous `GITHUB_TOKEN`
   (ces événements ne se déclenchent pas). Si un workflow `on: release` dédié est
   souhaité, faire tourner release-please avec un token de GitHub App / PAT.
6. **PyPI** : Trusted Publishing (OIDC), `pypa/gh-action-pypi-publish@release/v1`
   sans `user`/`password`, `permissions: id-token: write` au niveau du job publish,
   `environment: pypi`, `python -m build` en amont. Configurer le Trusted Publisher
   côté PyPI (repo + nom de workflow + environnement).
7. **Permissions** action : `contents: write`, `pull-requests: write`, `issues: write`
   + activer « Allow GitHub Actions to create and approve pull requests ».

## Sources

- release-please-action — README : <https://github.com/googleapis/release-please-action/blob/main/README.md>
- release-please-action — `action.yml` : <https://github.com/googleapis/release-please-action/blob/main/action.yml>
- release-please — `package.json` (v17.11.2) : <https://github.com/googleapis/release-please/blob/main/package.json>
- release-please — stratégie Python : <https://github.com/googleapis/release-please/blob/main/src/strategies/python.ts>
- release-please — updater `pyproject.toml` : <https://github.com/googleapis/release-please/blob/main/src/updaters/python/pyproject-toml.ts>
- release-please — updater `__version__` : <https://github.com/googleapis/release-please/blob/main/src/updaters/python/python-file-with-version.ts>
- release-please — `changelog-notes/default.ts` (types = changelogSections) : <https://github.com/googleapis/release-please/blob/main/src/changelog-notes/default.ts>
- release-please — doc « Customizing » (`extra-files`, `changelog-sections`) : <https://github.com/googleapis/release-please/blob/main/docs/customizing.md>
- release-please — doc « Manifest releaser » : <https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md>
- conventional-changelog-conventionalcommits — `constants.js` (défaut des types) : <https://github.com/conventional-changelog/conventional-changelog/blob/master/packages/conventional-changelog-conventionalcommits/src/constants.js>
- GitHub Docs — « GITHUB_TOKEN » (events non déclencheurs + exceptions) : <https://docs.github.com/en/actions/concepts/security/github_token>
- GitHub Changelog — GITHUB_TOKEN + workflow_dispatch/repository_dispatch (2022-09-08) : <https://github.blog/changelog/2022-09-08-github-actions-use-github_token-with-workflow_dispatch-and-repository_dispatch/>
- PyPI Docs — Trusted Publishers (index) : <https://docs.pypi.org/trusted-publishers/>
- PyPI Docs — « Using a publisher » (workflow OIDC, `id-token: write`, `on: release: published`, environment) : <https://docs.pypi.org/trusted-publishers/using-a-publisher/>
- pypa/gh-action-pypi-publish — README (`release/v1`, Trusted Publishing, `id-token: write` au niveau du job, non-goals) : <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/README.md>
