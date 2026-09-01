# Mentible — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Backend (FastAPI/Python), Mobile (React Native/Expo), Compiler (TypeScript/Node), Pipeline (vendored), **the shared `wegofwd-llm` seam package**, Infrastructure
**Last refresh:** 2026-09-01 (v2.1 — targeted update; measured on `origin/main@e13f10b`, v0.2.63, 1,354 commits. See **"Update — 2026-09-01"** below.)
**Prior refresh:** 2026-06-09 (v2.0 — major refresh; measured on disk at `40166ee`, branch `main`. **97 commits since v1.0**; new practice surfaces: the extracted `wegofwd-llm` provider seam (ADR-012), multi-provider BYOK, the BYOK 422-scrub fix (ADR-001), per-provider token clamping.)
**First analysis:** 2026-06-02 (v1.0, `e1c66f7`, branch `feat/authoring-regenerate-export-fixes`)
**Repo / brand:** `wegofwd2020-hub/Mentible` · public brand **Mentible**
**Related:** [mentible-critique.md](mentible-critique.md) · [mentible-development-pattern.md](mentible-development-pattern.md) · parent product: [studybuddy-practices.md](studybuddy-practices.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

> A catalogue of concrete practices observed in the Mentible codebase, with fixes. The through-line holds from v1.0: **the security practices are exemplary; the discipline gaps are all about the distance between an accepted decision (or a stale frame, or a drifted version pin) and the code that exists.** v2.0 adds a whole new practice surface — a *shared package seam* — which is well-executed but introduces the first cross-repo version-coupling debt.

---

## Update — 2026-09-01 (measured on `origin/main@e13f10b`, 1,354 commits)

- ✅ **Version-pin discipline held.** The v2.0 bad practice — `wegofwd-llm@v0.1.0` lagging the package's own `@v0.1.1` — is genuinely closed: `backend/requirements.txt` now pins the exact current tag (`@v0.2.0`). The underlying practice gap (git+https, no registry, no hash-pinning) is unchanged and has doubled: the second shared dependency `wegofwd-secure@v0.1.0` carries the same posture, plus a `requirements.txt` comment pinning `structlog`'s range transitively to satisfy it — a small, visible cost of the still-open registry gap.
- ❌ **The doc-drift bad practice didn't get fixed — it relocated to a worse form.** `CLAUDE.md` is now current and correctly tells readers `docs/STATUS.md` is canonical. But `docs/STATUS.md` itself is **717 commits stale** (last touched 2026-07-16, zero mentions of ADR-037 or the trust/validation Studio), and `project-status.yaml` still says `stage: pre-mvp`. **The anti-practice to name here is more specific than "stale docs": designating a document as canonical does not, by itself, keep it fresh — the designation needs its own update trigger** (a PR checklist item, a CI staleness check, anything), or it just becomes a more confident way to be wrong.
- ✅ **A wrong decision was reversed as visibly as it was made (new).** ADR-038 forced SME surfaces onto one palette; PRs #375/#376 reversed that restriction days later once it read as a UX bug, named in their own commit messages as reversing the ADR. Shipping a decision and then publicly reversing it in the open — rather than working around it quietly — is the same discipline this document has praised for *proposing* decisions, now shown for *un-shipping* one.
- ⚠️ **Partial Celery adoption, undocumented as a boundary (new).** New trust/topic-generation work (`backend/src/trust/tasks.py`) runs on Celery+Redis (`backend/src/core/celery_app.py`); the original `generate/export/library/structure` routers remain on in-process `BackgroundTasks`. Nothing states whether this split is a deliberate, permanent "new work only" boundary or an unfinished migration — worth a one-line ADR note either way, in a codebase that otherwise writes everything down.

---

## What changed since v1.0

- **New good practice surfaces:** the externalized `wegofwd-llm` seam (typed contract + registry + conformance loop + `py.typed`); the **BYOK 422-scrub fix** (a found key-echo leak, closed and tested); per-provider **output-token clamping** modeled as a capability, not a name-branch; the **validate→repair conformance loop** replacing blind retry; a migration-safe **multi-provider keystore**.
- **One v1.0 bad practice partly fixed:** `tests/llm/` is no longer pure orphans — `test_config.py` (15 funcs) is now real — but stale `__pycache__/*.pyc` for *deleted* modules persists.
- **One v1.0 bad practice persists, half-addressed as of v2.0, then regressed by 2026-09-01:** `CLAUDE.md` is now fixed and fresh, but the doc it designates canonical in its place (`docs/STATUS.md`) has since gone 717 commits stale — see "REGRESSED 2026-09-01" below.
- **One v2.0 bad practice, closed by 2026-09-01:** the lagging version pin — Mentible now pins `wegofwd-llm@v0.2.0`, an exact match.

---

## ✅ Good Practices

### ✅ Make the core security invariant an enforced test — even for a newly discovered leak

v1.0's exemplar was `test_no_key_in_logs.py`. v2.0 extends it: a real key-echo leak was found (FastAPI's default 422 handler echoes the request body, which on a missing-field error *is* the api_key) and locked with `test_missing_field_422_does_not_echo_key`, plus failed-job worker-error-path tests for both Anthropic *and* OpenAI keys. The backend `def test_` count rose 75 → **96**.

🔧 *Reusable takeaway:* when you find a leak outside your threat model, the fix isn't done until a test would fail if it regressed — and the test should name the exact vector (here, a *missing* field, not a malformed one).

### ✅ Scrub secrets on the way OUT, not just in logs

`scrub_validation_errors()` (`core/log_redaction.py:119`) redacts the BYOK key from the 422 *response body* two ways: **loc-based** (if the error targets a sensitive field, redact `input`/`ctx` wholesale — catching a too-short or non-`sk-ant-` key the value-regex would miss) and **value-based** (`_scrub_value` otherwise). The custom `@app.exception_handler(RequestValidationError)` in `main.py` mirrors FastAPI's default 422 shape but runs every error through it first.

🔧 *Takeaway:* a redaction layer that only covers logs is incomplete — any place you echo request data back (error bodies, debug endpoints) needs the same scrubber.

### ✅ Extract a shared seam as a package — with its contract, tests, and lint config

`wegofwd-llm` (773 LOC, 48 tests, tags v0.1.0/v0.1.1) is a typed `Provider`/`LLMRequest`/`LLMResponse`/`Capabilities` contract + a `ProviderSpec` registry + a `generate_validated` conformance loop, shipping `py.typed` (PEP 561) so consumers type-check against it. Its `pyproject.toml` **mirrors the consumers' ruff config** so a file lints identically in either repo. On disk its sole consumer is Mentible; ADR-012 intends Pramana as a second consumer, but the Pramana checkout imports nothing from it yet.

🔧 *Takeaway:* extract the *contract + tests + lint rules*, not just the code — otherwise consuming it is neither type-safe nor lint-clean. And prove the seam in production (Mentible ran it across five phases) before packaging — a forward-looking extraction for an anticipated second consumer is fine *if* the abstraction has already earned its shape in real use.

### ✅ Model provider quirks as capabilities, not name-branches

The Groq free-tier HTTP-413 (the fixed 16384 budget exceeded its ~12k ceiling) was fixed by adding `Capabilities.max_output_tokens` (0 = uncapped) to the contract and clamping `min(req.max_tokens, cap)` in the OpenAI-compatible provider — the *registry* declares each ceiling (groq/openrouter 8000, gemini 8192; OpenAI/Anthropic 0). A `min()`, never a floor, so small requests pass through unchanged.

🔧 *Takeaway:* when a provider rejects a request for a provider-specific reason, encode the limit as registry data, not an `if provider == "x"`.

### ✅ Validate→repair instead of blind retry

The worker routes through `generate_validated` (validate the model's JSON against the schema, and on a miss send a *targeted repair turn*) rather than re-rolling the entire generation N times. On a BYOK product this directly reduces wasted tokens on the user's bill.

### ✅ Multi-provider keystore that doesn't break existing installs

`mobile/src/secure/keyStore.ts` keeps Anthropic on the legacy `sbq_byok_key` storage key (no migration for existing installs) and namespaces others as `sbq_byok_key_{provider}`; the provider id matches the backend registry and `GenerationParams.provider` — one identifier across mobile, backend, and the seam.

### ✅ BYOK key lifecycle: encrypt-per-job, TTL, shred — on every path (unchanged, still strong)

`byok_envelope.py` AES-256-GCM under an HKDF-SHA256(master, salt=`job_id`) per-job key; `BYOK_MASTER_KEY` 64-hex with **no default**; TTL ~120 s; `finally` block `del api_key` + `DEL byok:{id}` on success and failure. Redaction by field-name *and* `sk-ant-` value-regex, now extended with a `<redacted-provider-key>` path for non-Anthropic keys.

### ✅ Vendor with recorded provenance; isolate the heavy runtime as a subprocess; single brand constant; config fails fast (all unchanged from v1.0, all still good)

`pipeline/VENDORED.md` SHAs; the key-free/network-free TS compiler subprocess; `mobile/src/constants/brand.ts`; `pydantic-settings` with no secret defaults.

---

## ⚠️ Bad Practices (and 🔧 fixes)

### ✅ CLOSED as of 2026-09-01 — the seam version pin now matches its dependency

`backend/requirements.txt` pins `wegofwd-llm[anthropic] @ git+https://...@v0.2.0`, an exact match with the package's own current tag. What v2.0 flagged here (a tag-behind-dependency drift) is fixed. **The underlying practice gap it was a symptom of — no registry, no hash-pinning, dependencies fetched live from a git URL — is unchanged, and has doubled**, since `wegofwd-secure@v0.1.0` (a second shared package) carries the identical posture. Publishing to a private registry with hash-pinning remains the fix; a bumped tag isn't that fix, it's just evidence the team is currently keeping up with it by hand.

### ⚠️ The seam is fetched from a git URL, not a registry (NEW)

`git+https://github.com/.../wegofwd-llm@<tag>` means every CI run and install builds the package from a live GitHub fetch — an availability and supply-chain coupling, with no hash-pinning.

🔧 Publish to a private PyPI / GitHub Packages and pin by version + hash. The git URL is fine for week-one bootstrapping; it shouldn't be the steady state.

### ⚠️ UPDATED 2026-09-01 — the Celery migration is now half-done, which is a new bad practice in its own right

v2.0's finding was "the plan says Celery, the code is still `BackgroundTask`." As of `main@e13f10b` that's no longer quite true: `backend/src/core/celery_app.py` + `trust/tasks.py` run the **new** trust/topic-generation work on Celery+Redis. But `generate/router.py`, `export/router.py`, `library/router.py`, and `structure/router.py` — the original, still-live generation/export paths a process restart can still silently drop — remain on in-process `BackgroundTasks`. **The new bad practice isn't "no Celery," it's "Celery for some routes and not others, with nothing written down about which is which or whether the split is permanent."**

🔧 Finish migrating the legacy routers to Celery, or add a one-line note (ADR or code comment) saying the split is intentional and why. A silent 50/50 job-runner architecture is harder to reason about than a fully-committed wrong choice.

### ⚠️ REGRESSED 2026-09-01 — canonical-doc freshness (was: "Doc drift... persists, half-fixed")

The v2.0/v1.0 finding here was that `CLAUDE.md` and `docs/STATUS.md` carried stale top-of-file frames. `CLAUDE.md` is now genuinely fixed — current, self-aware, and it explicitly designates `docs/STATUS.md` as *"the canonical, current 'what's built' record — read it first."* But `docs/STATUS.md` itself has since gone **717 commits stale** (last touched 2026-07-16, predating ADR-037 and the trust/validation Studio entirely), and `project-status.yaml` still reads `stage: pre-mvp`. **The practice lesson sharpens here: naming a doc "canonical" is a promise about its freshness, not a substitute for keeping it fresh — and an unfulfilled promise like that is a more confident way to mislead a reader than an un-designated stale doc ever was.**

🔧 Refresh `docs/STATUS.md` now (add ADR-037/the Studio, at minimum), and give the *canonical* designation itself an upkeep trigger — a PR-template checkbox tied to `docs/STATUS.md` the way the Help System's coverage gate is tied to feature/topic parity, or a CI staleness check on its own "Last updated" line.

### ⚠️ Stale `.pyc` orphans persist (partly fixed)

`tests/llm/test_config.py` is now real source (15 funcs), but `tests/llm/__pycache__/*.pyc` for *deleted* modules (`test_conformance`, `test_registry`, `test_anthropic_native`, `test_allowlist`, `test_openai_compatible`, `test_versioning`) still sits committed — those modules moved into the `wegofwd-llm` repo.

🔧 `git rm` the stale bytecode; add `__pycache__/` and `*.pyc` to `.gitignore` if not already enforced.

### ⚠️ Duplicated `16384` max-tokens defaults across the seam boundary (NEW)

`16384` is the default in `wegofwd_llm/contract.py`, `backend/.../tasks.py`, `pipeline/providers/base.py`, and `anthropic_caller.py`. With clamping now centralized in the seam, the pipeline-side legacy defaults are redundant and a drift risk.

🔧 Source the default budget from one place (the seam contract); delete the pipeline-side legacy constants.

### ⚠️ CORS `allow_origins=["*"]`, no auth, no rate-limit, no queue cap, all-zeros dev master key (all persist)

Unchanged from v1.0; all by-design MVP omissions, all still need closing before a public URL.

🔧 Lock CORS to app origins; add a per-IP rate limit + queue-depth cap; refuse the all-zeros master key when `APP_ENV != development`.

### ⚠️ Unversioned `book.json` contract on two boundaries (persists)

🔧 Add a `schema_version` field and validate on ingest at both backend↔compiler and OnDemand↔reader.

---

## 🔧 Testing practices — strong core, growing, missing the deployed edge

| Practice | State | Fix |
|---|---|---|
| Security path tested first (`test_no_key_in_logs`, 422-scrub, multi-provider error paths) | ✅ Excellent (75→96 backend tests) | — |
| Seam package independently tested (contract/registry/conformance/clamp) | ✅ Good (48 tests in `wegofwd-llm`) | Also exercise the seam from Mentible's CI at the pinned tag |
| Idempotency / export / structure / compiler / mobile tests | ✅ Good (compiler 71, mobile 132 blocks) | — |
| Per-provider clamp + validate→repair tested | ✅ Good | — |
| Live-provider verification | ⚠️ Self-reported only | Commit-message provenance (Groq→200, Anthropic tool-use); add an opt-in live smoke test gated on a secret |
| Deployed-backend E2E | ⚠️ Absent | Run one real BYOK generation against a deployed Fly instance |
| On-device mobile E2E | ⚠️ Absent | Detox/Maestro: multi-provider key-load → generate → poll → render |
| Direct `pipeline/` tests in this repo | ⚠️ Absent (transitive only) | Add schema/retry tests locally |

---

## Practices Scorecard (v2.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Mentible — Practices Scorecard (v2.1, 2026-09-01)                     │
├──────────────────────────────────────┬───────────┬───────────────────┤
│  Practice area                        │  Rating   │  Note (Δ vs v2.0)  │
├──────────────────────────────────────┼───────────┼───────────────────┤
│  BYOK key lifecycle (encrypt/TTL/shred)│  ✅ Strong │  unchanged         │
│  Secret redaction (logs + 422 response)│  ✅ Strong │  unchanged         │
│  Multi-provider key redaction         │  ✅ Strong │  unchanged         │
│  Shared seam as a typed package       │  ✅ Strong │  unchanged         │
│  Provider quirks as capabilities      │  ✅ Strong │  unchanged         │
│  Validate→repair (vs blind retry)     │  ✅ Strong │  unchanged         │
│  Vendoring with recorded provenance   │  ✅ Strong │  unchanged         │
│  Idempotency + bounded retry          │  ✅ Strong │  unchanged         │
│  Runtime isolation (compiler subproc) │  ✅ Strong │  unchanged         │
│  ADR decision discipline              │  ✅ Strong │  13 → 42 ADRs      │
│  Reversing a bad decision, in the open│  ✅ Strong │  NEW: ADR-038→#375 │
│  Config fail-fast / no secret defaults│  ✅ Good   │  unchanged         │
│  Seam version-pin currency            │  ✅ Fixed  │  now @v0.2.0 exact │
│  Dependency sourcing (git vs registry)│  ⚠️ Weak   │  unchanged, x2 pkgs│
│  Durable job execution                │  ⚠️ Weak   │  half-migrated:    │
│                                        │           │  Celery (new) vs   │
│                                        │           │  BackgroundTask    │
│  Canonical-doc freshness               │  🔴 Regressed│ STATUS.md 717   │
│                                        │           │  commits stale     │
│  Spec ↔ code frame reconciliation     │  ⚠️ Weak   │  half-fixed        │
│  Public-surface hardening (CORS/RL)   │  ⚠️ Weak   │  unchanged         │
│  Deployed + on-device test coverage   │  ⚠️ Gap    │  still not run     │
└──────────────────────────────────────┴───────────┴───────────────────┘
```

The shape is consistent and still telling: **everything that protects the user's key is strong**; the seam version pin is now genuinely current; and a new axis has appeared alongside the old MVP deferrals (jobs/CORS/auth) and reconciliation debt (version pins, half-fixed) — **canonical-doc freshness**, where designating a doc as the source of truth turned out not to be the same thing as keeping it one. None are architectural mistakes; all are cheap to close.

---

*Practices observed in the code on disk at `40166ee` (branch `main`), the `wegofwd-llm` package (latest tag `v0.1.1`), and `pramana` (HEAD `e2958ef`, branch `feat/ai-drafted-approved-content` — a cross-repo grep confirms Pramana does not yet import the seam). Where docstrings, `MVP_v1.md`, or `docs/STATUS.md` disagreed with the implementation, the implementation was treated as the source of truth. `pytest` was not runnable in the review environment, so test-pass claims rest on reading the asserting tests, not a green run. Supersedes v1.0 (2026-06-02 @ `e1c66f7`).*

*The **2026-09-01 update** reads `origin/main@e13f10b` (v0.2.63, 1,354 commits) via `git show origin/main:<path>`, not the local working tree. It is a targeted addition on top of the v2.0 body above, not a full re-derivation — the version-pin, Celery-migration, and canonical-doc findings were re-verified by grep (`requirements.txt`, `git log -- docs/STATUS.md`, `grep -rl BackgroundTasks backend/src`); the rest of the catalogue below is left as originally written at `40166ee`.*
