# Pramana — Good Practices, Bad Practices & How to Improve

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/pramana` |
| Branch | `main` |
| Git commit | `f23749f` (as of 2026-09-10) |
| Product version | 0.1.0 |
| Doc updated | 2026-09-13 |
| Last deployed | TODO — set last deployment date-time (not in git) |
<!-- doc-meta:end -->

**Reviewed:** 2026-09-13 (v1.0 — first review, against `main` at `f23749f`)
**Related:** [pramana-critique.md](pramana-critique.md) · [pramana-development-pattern.md](pramana-development-pattern.md)
**Rating key:** ✅ Good · ⚠️ Bad / Risk · 🔧 How to improve

---

## 1. Architecture Practices

### ✅ Good — Integrity by mechanism, not policy
Append-only audit log enforced by DB triggers (row **and** statement-level, so `TRUNCATE` can't break the chain — closed in migration `0011`); a pure, re-computable SHA-256 hash chain; evidence pinned to content versions. The compliance guarantee lives in the schema, not in a convention.

### ✅ Good — Pure, property-tested state machines with separation of duties
Assignment and content-approval lifecycles are explicit, pure, and hypothesis-tested; the producer of a video cannot attest it. Compliance-critical rules sit in one auditable place.

### ✅ Good — Regulation-agnostic engine
A framework is parsed data ("no definition, no request"); "none of them know what SOX is." New frameworks are content, not code.

### ⚠️ Bad — Multi-tenancy is schema-only
`tenant_id` is on every table but row-level isolation is deferred; ~16 manual `tenant_id ==` filters guard cross-tenant access, and one omission is a leak.
🔧 Before any second tenant, add a structural guard — a session-scoped tenant filter (SQLAlchemy event / RLS in Postgres) — so isolation can't depend on remembering a `WHERE` clause.

## 2. Testing Practices

### ✅ Good — 731 tests (~0.95:1), property-based, against a real database
Unit + integration + hypothesis; integration runs against real Postgres with a guard refusing non-test DBs and a considered `NullPool` choice. Behavioural safety tests: AST checks forbidding string-built SQL, a migration-identifier guard, a live hostile-payload injection test.

### ✅ Good — Coverage gate `fail_under = 80` with branch coverage, in CI.

### ❌ Bad — Migrations are never run in CI or tests
Integration tests build the schema from ORM metadata (`create_all`), not `alembic upgrade head`. The durability of the audit schema — the product's whole value — is first validated on the deploy box.
🔧 Add a CI step that runs `alembic upgrade head` (then `downgrade base` and up again) against the Postgres service, and ideally assert the migrated schema matches `Base.metadata`. This is the single highest-value test to add.

### ⚠️ Bad — The suite isn't reproducible from a cold clone
No in-repo venv; the suite needs Postgres + the git-pinned `wegofwd-*` deps, so `pytest` won't go green without CI-equivalent services.
🔧 Ship a `make test` / compose target that stands up Postgres+Redis and installs the extras, so a new machine can reproduce CI locally in one command.

## 3. Type Checking, Linting & Formatting

### ✅ Good — mypy `--strict` + ruff (black/isort/flake8 replacement), CI-gated
Strict typing with the pydantic plugin; an aggressive ruff select set (`S`/`ANN`/`DTZ`/`B`/`SIM`/`RUF`); clean even under a much newer ruff than pinned. Scoped, commented third-party overrides.

### ⚠️ Bad — `alembic/env.py` is unlinted (and dirty)
CI lints only `pramana tests scripts`; `alembic/env.py` carries a real `I001` nothing catches.
🔧 Add `alembic/env.py` to the linted paths (keep `alembic/versions` excluded).

## 4. Security & Secrets Practices

### ✅ Good — A candid, real threat model
`SECURITY.md` documents un-implemented controls as plainly as implemented ones (encryption at rest NOT done; two-role REVOKE no-op in single-role default; a `repr()` secret-leak recorded as a strict `xfail`). Honesty is itself a security practice.

### ✅ Good — Secret hygiene enforced, not just intended
`.env` symlinked outside the repo; credentials `SecretStr`; `SECRET_KEY` fail-closed; a `detect-private-key` pre-commit hook; a `test_secret_hygiene.py` asserting the invariants.

### ✅ Good — Real OIDC + RBAC + injection safety
Bearer-token verify (never issues), `require_roles`, entitlement checks, no user auto-provisioning; parameterised SQL with AST tests forbidding string-built queries and a live hostile-payload test.

### ⚠️ Bad — Bandit is the only scanner
No `pip-audit`/`semgrep`/Dependabot, despite two `git+https` deps and no lockfile.
🔧 Add `pip-audit` (or Dependabot) to CI; for a compliance product, dependency-vuln visibility is table stakes.

### ⚠️ Bad — Encryption at rest not implemented
Audit-log evidence is cleartext on disk (honestly flagged).
🔧 If the client's SOX posture requires it, this is a pre-go-live item, not a future-phase one — decide explicitly.

## 5. Migrations Practices

### ✅ Good — Single-head, linear, hand-curated
13 migrations, single base → single head, no branches; several carry real DDL (triggers, grants) autogenerate can't produce — evidence of deliberate authorship.

### ⚠️ Bad — Coherence is structural, not behaviourally verified (see §2), and the docs disagree on the baseline
README cites `0001→0006` and `0001→0009` in different places; the head is `0013`.
🔧 Run migrations in CI (§2 fix) and regenerate the README baseline references from the actual head.

## 6. Reproducibility & Packaging

### ✅ Good — Hardened container stack that actually stands the app up
Multi-stage Dockerfile, unprivileged uid 10001, scoped proxy headers, migrations deliberately not baked into the image; compose runs `postgres:16` → one-shot Alembic `migrate` → `api` on `127.0.0.1`.

### ✅ Good — Determinism argued and pinned where it's exercised
The `render` extra pins `torch`/`transformers` exactly, with a comment making the compliance-reproducibility case.

### ⚠️ Bad — No lockfile at the top level
Dependencies are range-pinned (`>=`) with two `git+https` tag pins; the transitive tree isn't frozen — a real reproducibility weakness for a product that argues for determinism.
🔧 Adopt `uv.lock` (or `pip-tools`) and commit it; it also unblocks `pip-audit`.

## 7. Process & Documentation Practices

### ✅ Good — Spec-first + SDD + TDD, reviewed pre-dispatch
Design spec → implementation plan (invoking `superpowers:subagent-driven-development` by name, failing-tests-first) → PR merge; plans were debugged against the real API before dispatch. 42 merges, PR-per-feature.

### ✅ Good — Status manifest with a drift-enforcing test
`project-status.yaml` drives the README status table, and a test fails if they diverge — real doc-meta discipline, and it tracks completeness separately from deployment.

### ✅ Good — The video pilot's refusal documented as a success
The human fidelity gate fired on the first generated lesson and the refusal is recorded verbatim. Treating a control that stopped bad output as the win it is, is exemplary compliance practice.

### ⚠️ Bad — ADRs cited everywhere, recorded nowhere in-repo; no CLAUDE.md
`ADR-011/013/026` are referenced throughout but no ADR file exists here; there is no house-rules `CLAUDE.md`.
🔧 Add pointer stubs for the cited ADRs (as kathai/other repos do for relocated ADRs) so references resolve, and a short `CLAUDE.md` capturing the compliance-critical house rules (append-only, separation-of-duties, no string-built SQL).

### ⚠️ Bad — The status table overstates "video complete"
`wegofwd-video integration ✅ Complete` means seam + gates; no shippable lesson exists (refused at the fidelity gate; Veo quota-blocked; local render unusable).
🔧 Split the status row into "seam + gates" (done) vs "a lesson that clears the fidelity gate" (open, VIDEO-1), so the manifest's honesty extends to this line too.

### ⚠️ Bad — Not deployed, and the repo can't confirm prod state
README/manifest say "not deployed"; the workflow is gated off; the repo names the `mambakkam.net` box (not the ops-note prod IP), while ops notes suggest a container instance runs on the box.
🔧 Reconcile: record the actual pre-launch deploy state in `SECURITY.md`/runbook so "not deployed" and "a container is running on the box" don't silently disagree.
