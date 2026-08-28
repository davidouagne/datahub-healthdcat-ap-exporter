# Politique de commits : merge-commit, Conventional Commits par commit, signoff DCO

Status: accepted

Contexte : carte wayfinder [#17](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/17)
(« Standards CI / release / dépendances / sécurité »), ticket
[#19](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/19).
Décision prise pour permettre l'automatisation de version et de changelog
(release-please, voir ADR-0003) et une provenance explicite des contributions.

## 1. Stratégie de merge : merge-commit uniquement

`main` n'accepte que le merge par **commit de merge**. `Squash and merge` et
`Rebase and merge` sont désactivés au niveau du dépôt. Conséquence : tous les
commits d'une branche de PR atterrissent sur `main` et sont lus par release-please
pour le calcul de version et le changelog.

Alternative écartée : **squash-only**. Plus simple pour un historique linéaire,
mais aurait fait dépendre le changelog du seul titre de PR. Le choix merge-commit
préserve un journal de Conventional Commits granulaire, au prix d'une exigence
d'historique de branche propre (§2).

## 2. Conventional Commits vérifiés par commit

Puisque chaque commit fusionné nourrit le changelog, **chaque commit** d'une PR
(hors commit de merge) doit être un Conventional Commit valide. Vérifié en CI par
`commitlint` (`wagoid/commitlint-github-action`) sur
`git rev-list --no-merges BASE..HEAD`. Le titre de PR est vérifié séparément
(`amannn/action-semantic-pull-request`) car il devient le corps du commit de merge.

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

Aucun contournement `if:` : humains et robots passent par les trois mêmes checks
(`dco`, `commitlint`, `pr-title`).

## Conséquences

- `Require linear history` est incompatible avec merge-commit → désactivé sur le
  ruleset `main`.
- Les workflows de politique de commits vivent dans
  `.github/workflows/commit-policy.yml` (3 jobs).
- `CONTRIBUTING.md` § « Style de commit » et un nouveau
  `.github/PULL_REQUEST_TEMPLATE.md` documentent `git commit -s` et l'exigence
  d'historique propre.
- ADR complémentaire : [0003 — Chaîne CI/CD](0003-chaine-ci-cd.md).
