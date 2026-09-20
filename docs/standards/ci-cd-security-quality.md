# CI/CD, security & quality standard

> **Source of truth**: this is the canonical copy of this document, maintained in
> `datahub-healthdcat-ap-exporter`. `datahub-yaml-source` holds (or will hold) an
> identical copy at the same path (`docs/standards/ci-cd-security-quality.md`),
> pointing back here. Kept in sync manually — no automated drift check between
> the two copies.
>
> Originated from a cross-repo comparison
> (`docs/research/ci-cd-security-quality-comparison-datahub-healthdcat-ap-exporter-vs-datahub-yaml-source.md`
> in `datahub-yaml-source`) and tracked as
> [`datahub-healthdcat-ap-exporter`#65](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/65)
> (this repo's changes) and
> [`datahub-yaml-source`#48](https://github.com/davidouagne/datahub-yaml-source/issues/48)
> (the sibling repo's changes, itself the larger effort — this repo was already
> closer to the target posture on most axes). This copy was authored here first
> because, at the time of writing, `datahub-yaml-source`#48 — which specs the
> doc as living there — hadn't created it yet; once it does, keep both in sync
> by hand.

Both repos are solo-maintained (`davidouagne`). This standard assumes that
baseline throughout — see [Scope & baseline](#scope--baseline).

## Scope & baseline

- **No required PR reviews, no `CODEOWNERS`** on either repo, while there is a
  single maintainer. This is a recorded decision, not an oversight — revisit
  when a second maintainer joins.
- **DCO sign-off enforcement is repo-specific, not part of this standard's
  mandate.** `datahub-healthdcat-ap-exporter` enforces it (`commit-policy.yml`,
  ADR-0002); `datahub-yaml-source` deliberately leaves it absent. Neither
  repo's posture here should be read as a target the other must adopt.
- **Dependabot auto-merge policy is a per-repo, hard-to-reverse decision**,
  recorded as its own ADR where adopted, not mandated identically by this
  standard.

## CI pipeline

- Parallel jobs, minimal `permissions: {}` at workflow level, elevated only
  where a job needs it (e.g. `id-token: write` for OIDC coverage upload).
- Baseline job set: `lint` (formatter + linter, blocking), `typecheck`
  (`mypy --strict` scoped to `src`, non-test code), `test` (matrix across the
  supported Python versions, `pytest` + coverage), a build/install smoke test.
- **`CI status` aggregate job**: `needs: [lint, typecheck, test, build, ...]`
  (whatever the repo's actual job set is), `if: always()`, fails if any
  dependency didn't succeed. Gives branch protection one stable check-run name
  instead of depending on brittle per-matrix-leg names.
- **Protection of `main`**: a single GitHub ruleset (not classic branch
  protection — never stack both: they apply cumulatively and drift apart).
  `required_status_checks` includes at minimum the `CI status` aggregate
  context, plus `dependency-review` where that job exists, plus the
  commit-policy checks where the repo has them; `strict: false`; PR required
  with no required approvals; repository-admin bypass; force-push and deletion
  blocked. A context is only addable once it has run at least once — sequence
  accordingly. `CI status` aggregates only the jobs of the CI workflow; checks
  from other workflows stay separate required contexts.
  *(Revised in `datahub-healthdcat-ap-exporter`: this repo moved from classic
  protection to the `main` ruleset, see ADR-0003 § Conséquences;
  `datahub-yaml-source` was verified live on 2026-09-20 to carry the same
  ruleset-only configuration.)*
- **`dependency-review-action`** on every PR (`fail-on-severity: high`, plus a
  license deny-list matching the repo's own license — e.g. GPL-2.0/3.0 and
  AGPL-3.0 variants for an Apache-2.0 project).

## Coverage

- **The real gate is `pytest --cov-fail-under=80` inside the `test` job** —
  not Codecov.
- **Codecov is purely informational**: both `project` and `patch` statuses set
  to `informational: true` in `codecov.yml`. A Codecov outage or a fork PR
  without an OIDC token can then never fail CI for a reason unrelated to real
  coverage.
- The Codecov-upload step itself: `fail_ci_if_error: false`, `if: always()` —
  it still attempts the upload even when `pytest` already failed the job on
  the coverage floor (pytest-cov writes the XML report before evaluating
  `--cov-fail-under`, so the file exists by then).

## Static analysis (SAST)

- **CodeQL default setup** (GitHub's built-in configuration, not a custom
  workflow file): `languages` scoped to the repo's actual languages
  (`python` + `actions` at minimum), `query_suite: default`,
  `threat_model: remote`, `schedule: weekly`.
- **Not added to the `main` ruleset's required contexts** — advisory/
  non-blocking by design on both repos.

## Dependency management

- **Dependabot**: the repo's package-manager ecosystem plus `github-actions`,
  at the root, weekly (Monday), grouped PRs where it reduces noise (e.g.
  dev-dependencies in one PR), `dependencies` label, an assignee.
- **Auto-merge**, where adopted: patch bumps everywhere and minor bumps for
  dev-only dependencies, gated on required checks being green. Majors and
  minor bumps to production dependencies always get manual review. This is a
  per-repo choice (see [Scope & baseline](#scope--baseline)).
- **Weekly SCA job** (e.g. `pip-audit`), independent of Dependabot's own
  schedule, opening or deduping a labeled issue on a real finding. The job
  itself only turns red if the tool fails to execute (network, resolution),
  not merely on finding a vulnerability — a finding is a signal, not a CI
  failure.

## Repo-level security settings

- **Secret scanning + push protection**: enabled.
- **Dependabot alerts**: enabled (distinct from Dependabot *security updates*,
  which can stay off if it would duplicate the SCA job / manual review flow
  above).
- **`SECURITY.md`** at the repo root: private "Report a vulnerability" GitHub
  flow (not a public issue), no formal SLA (solo maintainer), supported
  versions = `main` plus the latest tag.

## Commit & PR hygiene

- **Conventional Commits** enforced via `commitlint` against a
  `commitlint.config.mjs`, plus a semantic-PR-title check
  (`amannn/action-semantic-pull-request` or equivalent) — both real CI gates,
  not just documented conventions.
- **DCO**, where enforced: a check on every non-merge commit in the PR for a
  `Signed-off-by:` trailer. Repo-specific — see
  [Scope & baseline](#scope--baseline).
- **PR template** with a repo-specific self-check list (e.g. "regenerate
  generated docs/schema after a model change").

## Release automation

- **`release-please`** in manifest mode drives version bumps and changelog
  generation from Conventional Commit history — no hand-computed semver, no
  hand-written changelog.
- **PyPI publishing via Trusted Publishing** (OIDC, no stored token),
  `environment: pypi` with a required-reviewer protection rule on that
  environment.

## Out of scope for this standard

Supply-chain hardening beyond the above — OpenSSF Scorecard, blanket Action
pinning by SHA, SLSA build provenance — is a deliberate non-goal for both
repos today (see each repo's own ADR for the "standard Python complet, sans
durcissement supply-chain avancé" ambition). Reopen only as a fresh, scoped
effort if that ambition changes.
