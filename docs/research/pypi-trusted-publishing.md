# PyPI Trusted Publishing + OIDC — état de l'art 2026

Recherche préalable (ticket #23, wayfinder map #17) à la mise en place d'une
publication du paquet **`dh-healthdcat`** (l'exporteur) sur PyPI depuis GitHub
Actions, **sans token API long-lived**, via *Trusted Publishing* (OIDC), avec
**attestations PEP 740**, build via `uv build`, déclenchement **sur tags/releases
uniquement**.

Vérifié le 2026-08-28 contre les sources primaires listées en fin de document.

> **Périmètre — frontière explicite.** `actions/attest-build-provenance`
> (attestation *SLSA build provenance* stockée dans le magasin d'attestations
> GitHub, vérifiée par `gh attestation verify`) est **hors périmètre** de cet
> effort. Ce document ne traite que des attestations **PEP 740** que
> `pypa/gh-action-pypi-publish` émet **nativement** vers PyPI. Voir §5 pour la
> distinction précise.

---

## 1. Ce qu'est un *Trusted Publisher*

*Trusted Publishing* utilise OpenID Connect (OIDC) pour authentifier un job CI
auprès de PyPI **sans secret partagé**. Le fournisseur d'identité (GitHub
Actions) émet un jeton OIDC court, fortement vérifiable ; PyPI le valide contre
la configuration déclarée et **émet en retour un token API PyPI éphémère valable
15 minutes**, suffisant pour l'upload.
Source : <https://docs.pypi.org/trusted-publishers/>

- Fournisseurs OIDC supportés par PyPI : **GitHub Actions**, GitLab CI/CD, Google
  Cloud, ActiveState.
  Source : <https://docs.pypi.org/trusted-publishers/>
- Avantage vs token API classique : les tokens API PyPI sont *long-lived* ; un
  attaquant qui compromet un token peut l'utiliser jusqu'à révocation manuelle.
  Le token minté par Trusted Publishing expire en 15 min.
  Source : <https://docs.pypi.org/trusted-publishers/>
- `pypa/gh-action-pypi-publish` documente le flux : configurer le job avec la
  permission `id-token: write` **et sans** `user`/`password` explicites → le flux
  Trusted Publishing s'active automatiquement.
  Source : <https://github.com/pypa/gh-action-pypi-publish#trusted-publishing>

---

## 2. Setup côté PyPI

### 2a. Projet déjà publié sur PyPI

Sur <https://pypi.org/manage/projects/> → *Manage* sur le projet → onglet
*Publishing* de la barre latérale → section **GitHub Actions**, remplir :

| Champ PyPI | Valeur pour ce dépôt | Contrainte |
|---|---|---|
| *Repository owner's name* | `davidouagne` | org/compte GitHub, comparaison insensible à la casse |
| *Repository name* | `datahub-healthdcat-ap-exporter` | idem |
| *Workflow filename* | `release.yml` | **basename seul**, pas le chemin ; le fichier doit vivre dans `.github/workflows/` |
| *GitHub Actions environment name* | `pypi` | **optionnel mais « strongly recommended »** — active des restrictions supplémentaires (approbation manuelle par un sous-ensemble de mainteneurs de confiance) |

Cliquer *Add*.
Source : <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>

### 2b. Projet pas encore créé — *pending publisher*

Le projet `dh-healthdcat` n'existe pas encore sur PyPI → utiliser un **pending
publisher** : dans les réglages **du compte** (pas d'un projet, il n'existe pas
encore) → *Publishing* → formulaire GitHub Actions avec les **mêmes 4 champs +
le nom de projet PyPI** (`dh-healthdcat`).

- Un pending publisher **ne réserve pas le nom** tant qu'il n'a pas servi à
  publier. Si quelqu'un d'autre enregistre ce nom avant la première publication,
  le pending publisher est invalidé.
- À la première publication réussie, le projet est **créé automatiquement** et le
  pending publisher devient un trusted publisher normal.
Source : <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>

### 2c. Notes d'exploitation

- Le *Workflow filename* est comparé **exactement** ; renommer le workflow
  (ou le dépôt, ou le transférer) casse la publication tant que le publisher
  PyPI n'est pas mis à jour.
- Le champ *environment* PyPI doit correspondre **exactement** à la valeur
  `environment:` du job GitHub Actions (voir §3).
- On peut déclarer **plusieurs** trusted publishers sur un même projet (ex. un
  pour `release.yml` en prod, un pour TestPyPI).
Source : <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>

---

## 3. Setup côté workflow GitHub Actions

### 3.1 Permission `id-token: write`

- **Obligatoire** pour Trusted Publishing. À déclarer **au niveau du job** de
  publication uniquement, jamais globalement (moindre privilège ; empêche un
  script injecté dans le build de « voler sous le radar » pour élever ses
  privilèges).
  Sources :
  <https://github.com/pypa/gh-action-pypi-publish#trusted-publishing>,
  <https://docs.pypi.org/trusted-publishers/security-model/>
- `id-token: write` **ne donne aucun droit d'écriture** sur les ressources du
  dépôt : cela autorise seulement le workflow à *demander* et *utiliser* un jeton
  OIDC.
  Source : <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers>
- Dès qu'un bloc `permissions:` est déclaré, **toutes les portées non listées
  passent à `none`**. Le job de publication n'a besoin de rien d'autre que
  `id-token: write` (ajouter `contents: read` seulement si le job checkout le
  code ; `contents: write` seulement s'il crée aussi une *GitHub Release*).
  Source : <https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/control-permissions-for-github_token>

### 3.2 Environnement GitHub nommé `pypi`

Référencer `environment: name: pypi` dans le job : GitHub **applique les règles
de protection de l'environnement avant que le job démarre** et avant d'exposer
les secrets d'environnement.
Source : <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>

Règles de protection à configurer sur l'environnement `pypi`
(*Settings → Environments → pypi*) :

| Règle (nom exact GitHub) | Recommandation |
|---|---|
| **Required reviewers** (jusqu'à 6 users/teams, option *Prevent self-review*) | Activer — porte d'approbation manuelle avant chaque publication |
| **Wait timer** | Optionnel (ex. 0 ou quelques minutes) |
| **Deployment branches and tags** | Passer sur *Selected branches and tags* et ajouter une règle **tag** `v*` → l'environnement ne peut être utilisé que depuis un tag de release (défense en profondeur, en plus du garde `if:` du §6) |
| **Allow administrators to bypass configured protection rules** | À décider (désactiver pour un contrôle strict) |

Source : <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>

> Avec Trusted Publishing, l'environnement ne sert **pas** à héberger un secret :
> il sert de point d'application des règles de protection (revue manuelle,
> restriction aux tags). Ajouter un `url:` (ex.
> `https://pypi.org/p/dh-healthdcat`) est purement cosmétique (lien dans l'UI
> *Deployments*).

### 3.3 Version de `pypa/gh-action-pypi-publish`

- Référence recommandée par la doc officielle : **`pypa/gh-action-pypi-publish@release/v1`**
  (tag mouvant maintenu par la PyPA ; l'ancienne branche `master` est *sunset*).
  Source : <https://github.com/pypa/gh-action-pypi-publish#readme>
- **Durcissement recommandé** : épingler un **SHA de commit complet** plutôt que
  `release/v1` (ou un tag `vX.Y.Z` exact), et laisser Dependabot faire les bumps.
  Ne **pas** utiliser les branches mouvantes type `unstable/v1`.
  Source : <https://github.com/pypa/gh-action-pypi-publish#readme>
- Action de type **composite** ; ne tourne **que sous Linux** (`runner.os == 'Linux'`).
  Source : `action.yml` —
  <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/action.yml>
- **Ne pas** invoquer `pypi-publish` plus d'une fois dans le même job (non
  supporté), et **ne pas** l'utiliser dans une matrice — Trusted Publishing en
  *reusable workflow* est le seul cas explicitement **non supporté**.
  Source : <https://github.com/pypa/gh-action-pypi-publish#readme>
- Version publiée la plus récente au moment de la recherche : **v1.14.2**
  (série v1.14.x, mi-2026). Les attestations PEP 740 sont **activées par défaut
  depuis v1.11.0** (novembre 2024) — voir §5.
  Sources :
  <https://github.com/pypa/gh-action-pypi-publish/releases>,
  <https://github.com/pypa/gh-action-pypi-publish/releases/tag/v1.11.0>

### 3.4 Inputs de l'action (`with:`) et leurs défauts

Aucun input n'est requis pour le chemin Trusted Publishing (laisser `user` et
`password` **non renseignés** active le flux OIDC). Défauts effectifs relevés
dans `action.yml` (`release/v1`) :

| Input (kebab-case) | Défaut effectif | Rôle |
|---|---|---|
| `user` | `__token__` | ne pas surcharger en Trusted Publishing |
| `password` | *(non défini)* | **laisser vide** → déclenche OIDC ; le renseigner désactive le mode *secretless* |
| `repository-url` | `https://upload.pypi.org/legacy/` | mettre `https://test.pypi.org/legacy/` pour TestPyPI |
| `packages-dir` | `dist` | dossier des distributions à uploader |
| `attestations` | `true` | génère + upload les attestations PEP 740 (PyPI/TestPyPI + Trusted Publishing seulement) ; `false` pour désactiver |
| `verify-metadata` | `true` | `twine check` avant upload |
| `skip-existing` | `false` | ne pas échouer si le fichier existe déjà (à éviter en prod) |
| `verbose` | `true` | sortie détaillée |
| `print-hash` | `true` | affiche SHA256/MD5/BLAKE2-256 des fichiers uploadés |

Source : <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/action.yml>
et README (sections *Options* / *Disabling metadata verification* / *Tolerating
… duplicates* / *For Debugging*) —
<https://github.com/pypa/gh-action-pypi-publish#readme>

---

## 4. Construire `sdist` + `wheel` avec `uv build` et uploader `dist/`

- `uv build` construit le projet du répertoire courant et place les artefacts
  dans un sous-dossier **`dist/`**.
  Source : <https://docs.astral.sh/uv/guides/package/>
- **Par défaut, `uv build` construit d'abord une *source distribution* (sdist),
  puis une *wheel* à partir de cette sdist.** `uv build --sdist` ou
  `uv build --wheel` limitent à un seul format ; `uv build --sdist --wheel`
  force les deux depuis les sources.
  Source : <https://docs.astral.sh/uv/concepts/projects/build/>
- `uv build --no-sources` est recommandé avant publication pour vérifier que le
  paquet se construit sans `tool.uv.sources` (comme le ferait un consommateur
  via `pypa/build`).
  Source : <https://docs.astral.sh/uv/guides/package/>
- `--out-dir` (alias `-o`) change le dossier de sortie (défaut `dist/`).
  Source : <https://docs.astral.sh/uv/concepts/projects/build/>
- Ici le backend de build déclaré dans `pyproject.toml` est **hatchling** ;
  `uv build` respecte le backend PEP 517 déclaré, donc rien de spécial à faire.
- Côté publication : après `uv build`, uploader le **dossier `dist/` entier**
  (`packages-dir` par défaut = `dist`). `gh-action-pypi-publish` upload tous les
  fichiers du dossier (sdist `*.tar.gz` + wheel `*.whl`).
  Source : <https://github.com/pypa/gh-action-pypi-publish#readme>

> **Note sur `uv publish`.** `uv` sait aussi publier lui-même
> (`uv publish`, sans credentials en Trusted Publishing). **Mais `uv publish`
> n'émet pas d'attestations PEP 740** : l'exemple officiel Astral ajoute pour
> cela une étape `astral-sh/attest-action`. Comme les attestations *hors*
> `attest-build-provenance` sont un objectif de ce ticket et que
> `gh-action-pypi-publish` les fournit **sans étape supplémentaire**, on
> privilégie `uv build` (build) **+** `pypa/gh-action-pypi-publish` (publish).
> Source : <https://docs.astral.sh/uv/guides/integration/github/> (section
> *Publishing to PyPI*).

---

## 5. Attestations PEP 740 / Sigstore

### État par défaut

- **`pypa/gh-action-pypi-publish` génère et upload des attestations numériques
  signées pour tous les fichiers de distribution, activé PAR DÉFAUT pour tout
  projet en Trusted Publishing.** Introduit en opt-in en **v1.10.0**, basculé
  **on-by-default en v1.11.0** (novembre 2024).
  Sources :
  <https://github.com/pypa/gh-action-pypi-publish#generating-and-uploading-attestations>,
  <https://github.com/pypa/gh-action-pypi-publish/releases/tag/v1.11.0>,
  <https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/>
- PyPI a finalisé le support de **PEP 740** le **14 novembre 2024** ; les
  attestations sont **vérifiées à l'upload** (seules des attestations valides
  entrent dans l'index) et affichées sur la page du projet.
  Source : <https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/>
- Les objets d'attestation sont créés avec **Sigstore** pour chaque
  distribution, signés avec **l'identité fournie par le jeton OIDC GitHub du
  workflow courant** : l'authentification Trusted Publishing **et** les
  attestations sont donc liées à la **même identité**.
  Source : <https://github.com/pypa/gh-action-pypi-publish#generating-and-uploading-attestations>
- Contraintes : le support des attestations est **limité aux flux Trusted
  Publishing sur PyPI / TestPyPI** ; il **requiert** l'authentification par
  trusted publisher.
  Source : <https://github.com/pypa/gh-action-pypi-publish#generating-and-uploading-attestations>
- PyPI accepte au plus **2 attestations par fichier**, avec deux *predicate
  types* : *SLSA Provenance* et *PyPI Publish*.
  Source : <https://docs.pypi.org/attestations/>

### Comment désactiver / régler

```yaml
- uses: pypa/gh-action-pypi-publish@release/v1
  with:
    attestations: false   # défaut: true
```

Source : <https://github.com/pypa/gh-action-pypi-publish#generating-and-uploading-attestations>

### PGP

Le support des **signatures PGP a été déprécié puis retiré** par PyPI (beaucoup
de signatures n'étaient pas vérifiables). Les attestations PEP 740 basées sur
l'identité OIDC les **remplacent**. Il n'y a **plus** d'option PGP dans
`gh-action-pypi-publish`.
Source : <https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/>

### Frontière avec `actions/attest-build-provenance` (HORS périmètre)

| Aspect | `gh-action-pypi-publish` (attestations PEP 740) | `actions/attest-build-provenance` (HORS périmètre) |
|---|---|---|
| Standard | **PEP 740** (format d'attestation PyPI) | **SLSA Provenance v1** (in-toto) |
| Où c'est stocké / vérifié | Uploadé **sur PyPI** à côté du fichier, vérifié par PyPI à l'upload, visible sur la page projet | Magasin d'attestations **GitHub**, vérifié via `gh attestation verify` / API GitHub |
| Déclenchement | Automatique dans le step de publish (`attestations: true`) | Step séparé explicite dans le workflow |
| Identité | Jeton OIDC GitHub du workflow (Sigstore) | Jeton OIDC GitHub du workflow (Sigstore) |
| Permissions | `id-token: write` | `id-token: write` **+** `attestations: write` |

Les deux sont complémentaires mais **cet effort ne met en place que le premier**.
Ne pas ajouter `actions/attest-build-provenance` ni `astral-sh/attest-action`
dans le cadre du ticket #23.
Sources :
<https://github.com/pypa/gh-action-pypi-publish#generating-and-uploading-attestations>,
<https://docs.pypi.org/attestations/>

---

## 6. Conditionner la publication aux tags/releases (jamais sur `main`)

Trois verrous **cumulatifs** (défense en profondeur) :

1. **Trigger du workflow** — ne déclencher que sur tags :

   ```yaml
   on:
     push:
       tags:
         - "v*"
   ```

2. **Garde `if:` sur le job de publication** — recommandé par le README de
   l'action :

   ```yaml
   if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags')
   ```

   Source : <https://github.com/pypa/gh-action-pypi-publish#readme>

3. **Environnement GitHub `pypi`** — règle *Deployment branches and tags* limitée
   à un pattern de tag `v*`, + *Required reviewers*. GitHub refuse d'exécuter le
   job (donc l'accès OIDC élevé) si la ref ne matche pas.
   Source : <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>

Côté gouvernance dépôt : restreindre la **création/modification des tags `v*`**
aux mainteneurs (rulesets GitHub) — recommandation du modèle de sécurité PyPI
pour les workflows *tag-based*.
Source : <https://docs.pypi.org/trusted-publishers/security-model/>

Recommandations complémentaires du modèle de sécurité PyPI :

- Le job de publication doit idéalement n'avoir que **2 steps** : récupérer les
  dists produites par un **job de build séparé**, puis publier avec
  `pypa/gh-action-pypi-publish@release/v1`.
- **Séparer build et publish** en deux jobs, partager `dist/` via
  `actions/upload-artifact` → `actions/download-artifact`, afin qu'un script
  malveillant injecté au build ne puisse pas élever ses privilèges.
- Ne **jamais** utiliser `pull_request_target` pour ce type de workflow.
Sources :
<https://docs.pypi.org/trusted-publishers/security-model/>,
<https://github.com/pypa/gh-action-pypi-publish#trusted-publishing>

---

## 7. Workflow de référence (à créer : `.github/workflows/release.yml`)

> Fourni à titre de référence pour l'implémentation ultérieure ; ce ticket est
> une recherche, il ne crée pas le workflow. Nom de fichier `release.yml` à
> **enregistrer tel quel** côté PyPI (§2).

```yaml
name: Release to PyPI

on:
  push:
    tags:
      - "v*"

permissions: {}   # rien par défaut ; chaque job élève ce dont il a besoin

jobs:
  build:
    name: Build sdist + wheel
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<sha>          # v4.x
        with:
          persist-credentials: false
      - name: Install uv
        uses: astral-sh/setup-uv@<sha>        # vX.Y.Z
      - name: Build
        run: uv build --no-sources            # sdist puis wheel -> dist/
      - name: Check metadata
        run: uvx twine check dist/*
      - uses: actions/upload-artifact@<sha>   # v4.x
        with:
          name: dist
          path: dist/

  publish:
    name: Publish to PyPI (Trusted Publishing)
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags')
    environment:
      name: pypi
      url: https://pypi.org/p/dh-healthdcat
    permissions:
      id-token: write          # OBLIGATOIRE pour Trusted Publishing
    steps:
      - uses: actions/download-artifact@<sha> # v4.x
        with:
          name: dist
          path: dist/
      - name: Publish
        uses: pypa/gh-action-pypi-publish@<sha>   # release/v1 -> épingler un SHA
        # aucun input requis :
        #   - user/password laissés vides -> flux OIDC
        #   - packages-dir défaut "dist"
        #   - attestations défaut true  -> attestations PEP 740 émises
```

Sources de la structure :
<https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>,
<https://docs.astral.sh/uv/guides/integration/github/>,
<https://github.com/pypa/gh-action-pypi-publish#trusted-publishing>

---

## Recommandation

1. **Utiliser Trusted Publishing (OIDC), pas de token API.** Enregistrer un
   *pending publisher* côté PyPI pour `dh-healthdcat`
   (`davidouagne` / `datahub-healthdcat-ap-exporter` / `release.yml` / env
   `pypi`) ; le projet sera créé automatiquement à la première publication.
2. **Build avec `uv build --no-sources`** (sdist puis wheel dans `dist/`),
   **publish avec `pypa/gh-action-pypi-publish`** épinglé à un **SHA de commit**
   (piste `release/v1`, bumps Dependabot). On retient `gh-action-pypi-publish`
   plutôt que `uv publish` **parce qu'il émet les attestations PEP 740 sans
   étape supplémentaire**.
3. **Attestations PEP 740 : ne rien faire.** Elles sont **on-by-default** depuis
   `gh-action-pypi-publish` v1.11.0 et signées via l'identité OIDC du workflow.
   Laisser `attestations: true`. **Ne pas** ajouter
   `actions/attest-build-provenance` ni `astral-sh/attest-action` (hors
   périmètre).
4. **Trois verrous cumulés contre une publication sur `main`** : trigger
   `on: push: tags: ["v*"]`, garde
   `if: startsWith(github.ref, 'refs/tags')` sur le job publish, environnement
   `pypi` avec *Required reviewers* + *Deployment branches and tags* limité à
   `v*`. **Séparer build et publish** en deux jobs ; `id-token: write`
   uniquement sur le job publish ; `permissions: {}` au niveau workflow.
5. **Durcissement** : ruleset GitHub restreignant la création des tags `v*` aux
   mainteneurs ; `persist-credentials: false` au checkout ; épingler toutes les
   actions par SHA.

---

## Hand-off checklist (côté PyPI)

Pré-requis : compte PyPI avec 2FA, membre/owner (à venir) du projet
`dh-healthdcat`.

- [ ] **Cas projet inexistant (actuel)** — se connecter à PyPI →
      *Account settings* → *Publishing* → *Add a new pending publisher* →
      **GitHub Actions**.
- [ ] Renseigner :
  - [ ] *PyPI Project Name* : `dh-healthdcat`
  - [ ] *Owner* : `davidouagne`
  - [ ] *Repository name* : `datahub-healthdcat-ap-exporter`
  - [ ] *Workflow name* : `release.yml`  (basename exact, sans chemin)
  - [ ] *Environment name* : `pypi`
- [ ] *Add*. Vérifier que le pending publisher apparaît dans la liste.
- [ ] (Rappel : le nom `dh-healthdcat` n'est **pas** réservé tant qu'aucune
      publication n'a eu lieu — publier rapidement après création.)
- [ ] **Après première publication** : vérifier dans *Manage project →
      Publishing* que le trusted publisher est bien listé (plus « pending »).
- [ ] **Optionnel — TestPyPI** : répéter sur <https://test.pypi.org> avec un
      environnement GitHub `testpypi` distinct et un job publish dédié
      (`repository-url: https://test.pypi.org/legacy/`).
- [ ] Si le dépôt est un jour **renommé / transféré / le workflow renommé** :
      mettre à jour le publisher côté PyPI (sinon 403 à l'upload).

Côté GitHub (pour mémoire, non « PyPI side » mais bloquant) :

- [ ] Créer l'environnement `pypi` (*Settings → Environments*) avec *Required
      reviewers* et *Deployment branches and tags* = *Selected* + règle tag `v*`.
- [ ] Ruleset restreignant la création des tags `v*` aux mainteneurs.
- [ ] Créer `.github/workflows/release.yml` (cf. §7).

---

## Sources

Toutes consultées le 2026-08-28.

- PyPI — Trusted Publishers, overview : <https://docs.pypi.org/trusted-publishers/>
- PyPI — Adding a Trusted Publisher to an existing project : <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>
- PyPI — Creating a PyPI project with a Trusted Publisher (pending publisher) : <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>
- PyPI — Publishing with a Trusted Publisher (workflow recommandé) : <https://docs.pypi.org/trusted-publishers/using-a-publisher/>
- PyPI — Security model and considerations : <https://docs.pypi.org/trusted-publishers/security-model/>
- PyPI — Digital attestations (PEP 740) : <https://docs.pypi.org/attestations/>
- PyPI blog — « PyPI now supports digital attestations », 2024-11-14 : <https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/>
- PEP 740 — Index support for digital attestations : <https://peps.python.org/pep-0740/>
- `pypa/gh-action-pypi-publish` — README : <https://github.com/pypa/gh-action-pypi-publish#readme>
- `pypa/gh-action-pypi-publish` — `action.yml` (`release/v1`) : <https://github.com/pypa/gh-action-pypi-publish/blob/release/v1/action.yml>
- `pypa/gh-action-pypi-publish` — Releases : <https://github.com/pypa/gh-action-pypi-publish/releases>
- `pypa/gh-action-pypi-publish` — Release v1.11.0 (attestations on-by-default) : <https://github.com/pypa/gh-action-pypi-publish/releases/tag/v1.11.0>
- GitHub Docs — OIDC in cloud providers / `id-token: write` : <https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers>
- GitHub Docs — Control permissions for `GITHUB_TOKEN` : <https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/control-permissions-for-github_token>
- GitHub Docs — Managing environments for deployment (protection rules) : <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>
- Python Packaging User Guide — Publishing package distribution releases using GitHub Actions : <https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>
- uv — Building and publishing a package : <https://docs.astral.sh/uv/guides/package/>
- uv — Building distributions (`uv build`) : <https://docs.astral.sh/uv/concepts/projects/build/>
- uv — GitHub Actions integration (Publishing to PyPI) : <https://docs.astral.sh/uv/guides/integration/github/>
