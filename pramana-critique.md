# Pramana — Code Review & Critique

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
**Anchor:** `f23749f`
**Repo:** `pramana` (private, GitHub org `wegofwd2020-hub`)
**Phase:** `v0.1.0` — pre-release, **feature-complete on the core loop, not deployed** (production go-live gated off). Every tracked feature is code-complete; what remains is deployment and external sign-off.
**Scope:** A compliance training & tracking platform (FastAPI · SQLAlchemy 2.x async · PostgreSQL · Alembic · Celery/Redis) whose *primary product is auditable evidence*, not the course. A SHA-256 hash-chained, append-only audit log records every state change; evidence artifacts (quiz attempts, certificates) are pinned to the exact content version that produced them. First release is scoped to **SOX for a single named corporate client** (name withheld), single-tenant. Content is authored via a two-gate human-approval state machine; the LLM/video generation seams are injectable and the whole loop runs with zero model calls.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [pramana-development-pattern.md](pramana-development-pattern.md) · [pramana-practices.md](pramana-practices.md)

---

## Executive Summary

`pramana` is the most *disciplined* codebase in the portfolio and, on engineering practice, the strongest. In ~4 months and 190 commits it has reached feature-complete on its core loop (14,096 production LOC / 13,396 test LOC, **731 test functions across 79 files**, ~0.95:1 test-to-code, including property-based domain tests), behind a CI pipeline that runs `ruff` + `mypy --strict` + `bandit` + `pytest` against a **real Postgres 16 and Redis 7** — not fakes. It is built around one genuinely good idea, executed consistently: **compliance is architectural, not bolt-on.** Every mutation appends to a hash-chained, append-only audit log (row *and* statement-level triggers, so even `TRUNCATE` can't break the chain — a hole found and closed in migration `0011`); the audit hash is a pure, re-computable function; quiz attempts pin the question version and the then-correct answer; certificates render only from pinned facts. The real deliverable is a tamper-evident evidence trail, and the code treats it that way.

The second defining quality is **honesty**, and it is unusual. `SECURITY.md` is a real STRIDE-lite threat model that documents what is *not* done as plainly as what is: "encryption at rest — NOT IMPLEMENTED, verified 2026-09-09"; the two-role `REVOKE` control is a no-op in the single-role default and says so; a secret-in-`repr()` gap is recorded as a strict `xfail` rather than hidden. The deploy runbook is equally candid that the production path "has never been stood up." A `project-status.yaml` manifest marks all ~24 features `done` — but "done" is defined as code-complete, and the summary states in the same breath that the product is "not yet deployed." A test enforces that the README status table never drifts from the manifest. This is a codebase that refuses to overstate itself — which makes the one place its status table *does* overstate stand out sharply.

That place is **video**. The status table reads `wegofwd-video integration ✅ Complete`, and the *seam* genuinely is — but **no shippable lesson video has ever been produced.** The one real render (a local CPU LTX-Video path, since Veo is quota-blocked) ran for 98 minutes, came out silent, hallucinated on-screen text in all five scenes, and was **refused by a human at the fidelity-attestation gate** — quoted in the pilot log in the reviewer's own words ("nothing in this video made me feel I was learning anything"). The right way to read this is the way the repo does: **the control worked.** `publish_draft` refuses the unattested draft; `attach_course_video` raises rather than stamping a fake success; the pilot is documented as a gate that fired, not a feature that shipped. But a critique must be precise: "video integration complete" means the seam and the gates, not a delivered lesson, and VIDEO-1 remains the open edge of the project.

The engineering gaps are narrow and specific. **Migrations are never run in CI or tests** — integration tests build the schema from ORM metadata (`create_all`), so migration correctness is first validated on the deploy box, not in the pipeline; this is the single most important gap for a product whose value is a durable audit schema. There is **no lockfile** (dependencies are range-pinned, two via `git+https` tags) — a real reproducibility weakness for a product that argues at length for determinism elsewhere. **Dependency-vulnerability scanning is absent** (bandit only; no `pip-audit`/`semgrep`/Dependabot). **Multi-tenancy is schema-only** — every table carries `tenant_id`, but row-level isolation is deliberately deferred past v1. And the "Phase 0 / contracts-first, no-LLM" framing from the portfolio strategy is *not* a concept that exists in this repo by name — though its substance (Protocol seams, `Null`/fake provider defaults, a provider-free end-to-end test, fail-closed provider construction) is genuinely built.

**Verdict:** The portfolio's best-engineered product and its most honest — a compliance platform whose audit-trail-as-product thesis is real, tested, and coherent, delivered with CI-enforced strict typing, linting, and real-database tests. It is feature-complete and deployable but **not deployed**, and blocked on external gates (a named client committing, legal/framework content sign-off, and the open video pilot) rather than on code. Its most material technical gaps are that migrations are untested in CI and there is no lockfile; its most material *product* gap is that the video lesson — the thing the pilot exists to prove — does not yet clear a human's fidelity bar.

## Snapshot

| Dimension | Measured @ `f23749f` |
|---|---|
| Version | `0.1.0` (`pyproject.toml`) |
| Production LOC | 14,096 (`pramana/`) |
| Test LOC | 13,396 |
| Tests | **731 functions, 79 files** (unit + integration + property/hypothesis) — **CI-verified** vs real Postgres 16 + Redis 7; not locally re-run here (no in-repo venv; suite needs Postgres + the git-pinned deps) |
| Test-to-source LOC ratio | ~0.95:1 |
| Commits on `main` | 190 (42 merges, PRs to #49), 2026-05-05 → 2026-09-10 (~4 months, bursty — Sept ≈ 103) |
| mypy | ✅ `strict = true` (+ pydantic plugin, `warn_unused_ignores`, `disallow_untyped_defs`) |
| ruff | ✅ clean on `pramana tests scripts` (replaces black/isort/flake8; aggressive select incl. `S`/`ANN`/`DTZ`) — ⚠️ `alembic/env.py` has 1 unlinted `I001` (excluded from CI scope) |
| Coverage | `branch=true`, `fail_under=80` (implicit via pytest-cov; no published number) |
| CI | ✅ `ruff` + `mypy --strict` + `pytest` (real PG+Redis services) + `bandit` on push/PR — ⚠️ **matrix of one** (3.12), **migrations NOT run**, Docker image not built |
| SAST / dep-scan | ⚠️ **bandit only** — no `pip-audit`/`semgrep`/Dependabot despite 2 `git+https` deps + no lockfile |
| Lockfile | ❌ none (range-pinned; `wegofwd-llm@v0.1.1`, `wegofwd-video@v1.1.0` by tag) |
| DB tables / migrations | 23 tables / 13 migrations (single base `0001` → single head `0013`, linear) |
| Audit integrity | SHA-256 hash-chained append-only log; row **and** statement-level (`TRUNCATE`) triggers (`0011`) |
| LLM / video seams | **External** git-pinned `wegofwd-llm[anthropic]` + `wegofwd-video` (not vendored); injectable, fail-closed without a key |
| Video lesson output | ⚠️ seam + gates complete, **zero shippable lesson** (refused at human fidelity gate; Veo quota-blocked, local render unusable) |
| Frameworks | SOX = only validated scope; FCPA + GDPR/HIPAA/ISO/PCI = authored story libraries only ("future phase") |
| Multi-tenancy | ⚠️ schema-only (`tenant_id` everywhere; row-level isolation deferred past v1) |
| Deployed? | ❌ Repo says **not deployed** (deploy workflow gated off via `PRAMANA_DEPLOY_ENABLED`); a container instance appears to run on the prod box per ops notes, but not customer-live |
| Launch blockers | External: a named client committing, legal/framework content sign-off, VIDEO-1 fidelity gate, + infra the app can't provision (two-role DB, S3 Object-Lock) |

## 1. Architecture

### Strengths
- ✅ **Audit-trail-as-product.** A SHA-256 hash-chained, append-only `audit_log` with a pure re-computable hash and DB-level immutability (row + statement `TRUNCATE` triggers). Evidence (attempts, certificates) is pinned to the content version that produced it. This is the differentiator and it is real in the schema.
- ✅ **Two explicit state machines, both pure and property-tested** — assignment (`ASSIGNED/IN_PROGRESS/PASSED/BLOCKED/CANCELLED/EXPIRED`, one-in-progress + max-attempts + cooldown invariants) and content-approval (`RECEIVED→…→PUBLISHED/REJECTED`) with **separation-of-duties** and a distinct video-attestation gate.
- ✅ **Regulation-agnostic engine.** A framework is *data* (parsed from `###` clause anchors by a definitions library, "no definition, no request"); "none of them know what SOX is." Adding FCPA/GDPR/… is content, not code.
- ✅ **Injectable seams, model-free-runnable.** LLM/video are Protocol interfaces with `Null`/fake defaults; the end-to-end pilot test drives both approval gates with no provider constructed. Provider construction fails closed without a key.

### Gaps & Risks
- ⚠️ **Multi-tenancy is schema-only** — `tenant_id` on every table (FK `RESTRICT`), but row-level isolation is deferred past v1; a missing `tenant_id ==` filter in any query would be a cross-tenant leak, and this isn't yet enforced structurally.
- ⚠️ **The 569-line `api/dependencies.py`** is the DI hub to watch; `api/schemas.py` (692) and `services/assignments.py` (615) are the other large modules. None egregious.

## 2. Code Quality

### Strengths
- ✅ **mypy `--strict` (CI-gated)** with the pydantic plugin and belt-and-suspenders warnings; third-party loosening is scoped + commented.
- ✅ **ruff clean** on `pramana tests scripts` (even under a much newer ruff than pinned), replacing black/isort/flake8 with an aggressive select set (`S`, `ANN`, `DTZ`, `B`, `SIM`, `RUF`).
- ✅ **Zero `TODO`/`FIXME`/`HACK`** in `pramana/` — unfinished work lives in `TICKETS/` and `SECURITY.md`, not scattered in code.

### Gaps & Risks
- ⚠️ **`alembic/env.py` is unlinted** — CI lints only `pramana tests scripts`, and it carries a real `I001` import-sort error. Minor, but it's the migration bootstrap.
- ⚠️ **No lockfile** — dependencies are range-pinned (`>=`) with two `git+https` tag pins; not byte-for-byte reproducible, which is a weakness for a product whose own docs argue for determinism.

## 3. Test Coverage

### Strengths
- ✅ **731 tests / 79 files (~0.95:1)**, including **property-based** state-machine tests (hypothesis) and integration tests against **real Postgres**, with a safety guard refusing non-test databases and a well-reasoned `NullPool` choice.
- ✅ **Coverage gate `fail_under = 80`** with branch coverage, run in CI.
- ✅ **Behavioural safety tests**: AST tests forbidding string-built SQL, a migration-identifier guard, a live hostile-payload injection test, and a secret-hygiene test asserting credentials are `SecretStr`.

### Gaps & Risks
- ❌ **Migrations are never exercised in CI or tests.** Integration tests build the schema via `create_all` (ORM metadata), not `alembic upgrade head` — so migration correctness (the durability of the audit schema) is first validated on the deploy box. Biggest gap in the suite.
- ⚠️ **Coverage number is implicit and unpublished** (gate honored via config, not an explicit `--cov-fail-under`; artifact uploaded, no badge).
- ⚠️ **Not locally reproducible without setup** — no in-repo venv; the suite needs Postgres + the git-pinned `wegofwd-*` deps, so a cold clone can't `pytest` green without CI-equivalent services (this review verified counts by grep and relied on CI for the pass state).

## 4. Documentation

### Strengths
- ✅ **`SECURITY.md` is a standout** — a real threat model, candid about un-implemented controls (encryption at rest, two-role REVOKE no-op, a `repr()` secret-leak `xfail`).
- ✅ **README status table auto-generated from `project-status.yaml`** with a drift-enforcing test — genuine doc-meta discipline.
- ✅ **Extensive design corpus** — numbered design docs (`00`–`03`, `02_resolved_decisions.md` a locked v1 spec), 6 framework references, ~60 user stories, an OpenAPI spec, and superpowers plans/specs.

### Gaps & Risks
- ⚠️ **ADRs are cited but not recorded in-repo.** `ADR-011` (Mentible content-integration), `ADR-013`, `ADR-026` (wegofwd-video) are referenced throughout code/docs, but no ADR file exists here — authority a reader of this repo cannot open (shared-engine convention, but still a gap).
- ⚠️ **Doc drift.** README cites the migration baseline as `0001→0006` and `0001→0009` in different places while the head is `0013`; the VIDEO-1 ticket contradicts itself on a transcript gap the code has since closed.
- ⚠️ **No `CLAUDE.md`** house-rules file (unusual for this portfolio).

## 5. Security & Safety

### Strengths
- ✅ **Real OIDC + RBAC** — bearer-token verification (verifies, never issues), `require_roles`, entitlement checks, no auto-provisioning of users.
- ✅ **Injection-safe by construction + tested** — AST tests forbidding string-built SQL, a live hostile-payload test, parameterised everywhere.
- ✅ **Secret hygiene enforced** — `.env` symlinked outside the repo, credentials `SecretStr`, `SECRET_KEY` fail-closed, a `detect-private-key` pre-commit hook.
- ✅ **Hardened Dockerfile** — multi-stage, unprivileged uid 10001, scoped proxy headers, migrations deliberately *not* in the image.

### Gaps & Risks
- ⚠️ **Bandit is the only scanner** — no `pip-audit`/`semgrep`/Dependabot, which matters given two `git+https` deps and no lockfile.
- ⚠️ **Encryption at rest is not implemented** (audit log cleartext on disk) — honestly documented, but a real gap for special-category compliance evidence.
- ⚠️ **Cross-tenant isolation is not structurally enforced** (schema-only; ~16 manual `tenant_id` filters) — plausible but unverified, and one omission is a leak.

## 6. Scalability & Operations

### Strengths
- ✅ **Coherent container stack** — `postgres:16` (healthcheck) → one-shot `migrate` (Alembic) → `api` (waits on migrate, binds `127.0.0.1` only). `compose.deploy.yaml` mirrors it with `restart: always` and no exposed DB port.
- ✅ **Deploy pipeline built + candid** — gated auto-deploy (`PRAMANA_DEPLOY_ENABLED`), pinned SSH host key (no TOFU), retrying smoke test, incident-issue on failure, **no auto-rollback by design** (bad migrations aren't fixed by redeploy). The runbook documents its own un-provisioned prerequisites.

### Gaps & Risks
- ⚠️ **Not deployed / deployment unconfirmed by the repo.** README + manifest say "not yet deployed"; the workflow is gated off; the repo names the `mambakkam.net` box (not the ops-note prod IP). A container instance appears to run on the prod box per ops notes — so the honest read is *a pre-launch instance may exist, but there is no customer go-live and the repo cannot confirm a live prod.*
- ⚠️ **Migrations first validated on the box**, not in CI (see §3) — the operational risk that pairs with the untested-migration gap.
- ⚠️ **Launch is gated on people, not code** — a named client committing (which also decides single- vs multi-tenant), legal/framework sign-off, the VIDEO-1 fidelity gate, and infra the app can't provision (two-role DB topology, S3 Object-Lock bucket).
