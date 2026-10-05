# Politique de commits : merge par rebase, Conventional Commits par commit, signoff DCO

Status: accepted

Contexte : carte wayfinder [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17)
(« Standards CI / release / dépendances / sécurité »), ticket
[#19](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/19).
Décision prise pour permettre l'automatisation de version et de changelog
(release-please, voir ADR-0003) et une provenance explicite des contributions.

## 1. Stratégie de merge : rebase uniquement

*(Révisé le 2026-10-05 — voir Conséquences : le merge-commit d'origine dupliquait
chaque entrée du changelog.)*

`main` n'accepte que le **merge par rebase** (`Rebase and merge`). Le commit de
merge et `Squash and merge` sont désactivés au niveau du dépôt et du ruleset
`main` (`allowed_merge_methods: ["rebase"]`), qui exige en outre un historique
linéaire. Conséquence : tous les commits d'une branche de PR atterrissent tels
quels sur `main`, sans commit de merge, et sont lus par release-please pour le
calcul de version et le changelog. Une branche se met à jour par rebase
(« Update with rebase »), pas en y fusionnant `main`.

Alternatives écartées :

- **squash-only** : aurait fait dépendre le changelog du seul titre de PR. Le
  rebase préserve un journal de Conventional Commits granulaire, au prix d'une
  exigence d'historique de branche propre (§2).
- **merge-commit** (choix initial) : GitHub place toujours le titre de PR dans le
  commit de merge (en sujet ou en corps : les seules combinaisons acceptées sont
  `PR_TITLE`/`PR_BODY`, `PR_TITLE`/`BLANK`, `MERGE_MESSAGE`/`PR_TITLE`).
  release-please y lit un Conventional Commit en plus de ceux de la branche et
  n'offre aucune option pour ignorer les commits de merge : chaque entrée du
  changelog apparaissait en double (0.1.3 à 0.1.9).

## 2. Conventional Commits vérifiés par commit

Puisque chaque commit fusionné nourrit le changelog, **chaque commit** d'une PR
doit être un Conventional Commit valide. Vérifié en CI par `commitlint`
(`wagoid/commitlint-github-action`) sur `git rev-list --no-merges BASE..HEAD`.
Le titre de PR n'entre pas dans l'historique (merge par rebase, §1) : il n'est
plus vérifié (contrôle `pr-title` / `amannn/action-semantic-pull-request`
retiré le 2026-10-05).

Config `commitlint` : `type-enum = [feat, fix, test, docs, chore, build]`,
`header-max-length: 72`, `subject-full-stop: never`, `type-empty` /
`subject-empty: never`, scopes libres, pas de `subject-case`. Le contributeur
nettoie l'historique de sa branche (rebase interactif) avant d'ouvrir la PR.

## 3. Signoff DCO

Chaque commit doit porter un trailer `Signed-off-by:` (Developer Certificate of
Origin). Vérifié par un script inline (`git rev-list --no-merges` +
`grep -E '^Signed-off-by: .+ <.+>$'`), **non rétroactif** : l'historique antérieur
à l'adoption n'est pas réexaminé (bornage `BASE..HEAD`). Complété par le réglage
dépôt « Require contributors to sign off on web-based commits ».

Alternative écartée : exiger une **signature cryptographique GPG/S-MIME**.
Rejetée : friction forte pour les contributeurs externes, hors de l'ambition
« standard Python » ; le DCO couvre l'intention de provenance, et les commits de
bots ou faits via l'UI GitHub sont déjà « Verified » par GitHub.

## 4. Robots

- **release-please** : l'option `signoff` de l'action ajoute le trailer à son
  commit `chore(main): release …` → passe le check `dco` sans exception.
- **Dependabot** : ses commits portent déjà `Signed-off-by: dependabot[bot]` ;
  son `commit-message.prefix` est maintenu dans le `type-enum` (`build(deps): …`).

Aucun contournement `if:` : humains et robots passent par les deux mêmes checks
(`dco`, `commitlint`).

## Conséquences

- `Require linear history` est **activé** sur le ruleset `main`
  (`required_linear_history`) depuis le passage au rebase ; il était désactivé
  tant que le merge-commit s'appliquait.
- Les workflows de politique de commits vivent dans
  `.github/workflows/commit-policy.yml` (2 jobs : `dco`, `commitlint` ; le job
  `pr-title` et le déclencheur `pull_request_target` sont retirés).
- **Révisé le 2026-10-05 (merge-commit → rebase)** : les releases 0.1.3 à 0.1.9
  listaient chaque entrée de changelog deux fois, une fois pour le commit de
  branche et une fois pour le commit de merge, dont le titre de PR était lu par
  release-please. Le rebase supprime le commit de merge et, avec lui, la raison
  d'être du contrôle `pr-title` (retiré du workflow et des contextes requis du
  ruleset). Les commits rebasés sont réécrits par GitHub (nouveaux SHA) mais
  conservent leur trailer `Signed-off-by`. L'auto-merge Dependabot passe à
  `gh pr merge --auto --rebase` (ADR-0003 §4).
- `CONTRIBUTING.md` § « Style de commit » et un nouveau
  `.github/PULL_REQUEST_TEMPLATE.md` documentent `git commit -s` et l'exigence
  d'historique propre.
- ADR complémentaire : [0003 — Chaîne CI/CD](0003-chaine-ci-cd.md).
