# Mentible — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** Backend (FastAPI/Python), Mobile (React Native/Expo), Compiler (TypeScript/Node), Pipeline (vendored), **the shared `wegofwd-llm` seam package**, Infrastructure
**Last refresh:** 2026-06-09 (v2.0 — major refresh; measured on disk at `40166ee`, branch `main`. **97 commits since v1.0**; new practice surfaces: the extracted `wegofwd-llm` provider seam (ADR-012), multi-provider BYOK, the BYOK 422-scrub fix (ADR-001), per-provider token clamping.)
**Prior refresh:** 2026-06-02 (v1.0 — first analysis, `e1c66f7`, branch `feat/authoring-regenerate-export-fixes`)
**Repo / brand:** `wegofwd2020-hub/Mentible` · public brand **Mentible**
**Related:** [mentible-critique.md](mentible-critique.md) · [mentible-development-pattern.md](mentible-development-pattern.md) · parent product: [studybuddy-practices.md](studybuddy-practices.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

> A catalogue of concrete practices observed in the Mentible codebase, with fixes. The through-line holds from v1.0: **the security practices are exemplary; the discipline gaps are all about the distance between an accepted decision (or a stale frame, or a drifted version pin) and the code that exists.** v2.0 adds a whole new practice surface — a *shared package seam* — which is well-executed but introduces the first cross-repo version-coupling debt.

---

## What changed since v1.0

- **New good practice surfaces:** the externalized `wegofwd-llm` seam (typed contract + registry + conformance loop + `py.typed`); the **BYOK 422-scrub fix** (a found key-echo leak, closed and tested); per-provider **output-token clamping** modeled as a capability, not a name-branch; the **validate→repair conformance loop** replacing blind retry; a migration-safe **multi-provider keystore**.
- **One v1.0 bad practice partly fixed:** `tests/llm/` is no longer pure orphans — `test_config.py` (15 funcs) is now real — but stale `__pycache__/*.pyc` for *deleted* modules persists.
- **One v1.0 bad practice persists, half-addressed:** the doc-drift (`CLAUDE.md`/`SCOPE.md`/`STATUS.md`) got ADR amendment *notes* but the stale top-of-file frames remain.
- **One new bad practice:** **a lagging version pin** — Mentible pins `wegofwd-llm@v0.1.0`; the package is already at `@v0.1.1`.

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

### ⚠️ The seam version pin already lags its dependency (NEW)

Mentible's `backend/requirements.txt` pins `wegofwd-llm[anthropic] @ git+https://...@v0.1.0`; the package is already at `@v0.1.1` (a `py.typed`/PEP 561 fix). The sole consumer is a tag behind its own dependency in the same week the seam shipped — and that will become genuine *cross-consumer* drift the moment Pramana (ADR-012's intended second consumer) wires it.

🔧 Bump Mentible to `@v0.1.1`, and add a lightweight cross-repo version check (or a shared constraints file) before a second consumer exists. A shared package's whole value is one source of truth — defeated the moment a consumer drifts.

### ⚠️ The seam is fetched from a git URL, not a registry (NEW)

`git+https://github.com/.../wegofwd-llm@<tag>` means every CI run and install builds the package from a live GitHub fetch — an availability and supply-chain coupling, with no hash-pinning.

🔧 Publish to a private PyPI / GitHub Packages and pin by version + hash. The git URL is fine for week-one bootstrapping; it shouldn't be the steady state.

### ⚠️ The plan says Celery; the code is still an in-process `BackgroundTask` (persists)

A process restart silently drops in-flight (minutes-long) jobs and leaves an encrypted envelope in Redis until TTL. `MVP_v1.md` still says "Celery."

🔧 Implement the Celery/Redis worker, or make the spec tell the truth with a one-line user-visible caveat. Don't let three documents disagree.

### ⚠️ Doc drift: `CLAUDE.md`/`SCOPE.md`/`STATUS.md` frames are still stale (persists, half-fixed)

`CLAUDE.md`/`SCOPE.md` got ADR-009/ADR-004 amendment *notes*, but `CLAUDE.md`'s status header still says "**Pre-MVP — directory stubs only, no application code yet**" over ~13k LOC, and `docs/STATUS.md` is still "Last updated 2026-05-26, branch `feat/mobile-skeleton`" — ~140 commits stale, predating multi-provider, books-only, and the seam package.

🔧 **Fix the headers, don't just append notes.** An ADR is half-done until the durable frame it changes is rewritten — and a layered note over a "directory stubs only" header reads as more wrong, not less.

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
│  Mentible — Practices Scorecard (v2.0)                                │
├──────────────────────────────────────┬───────────┬───────────────────┤
│  Practice area                        │  Rating   │  Note (Δ vs v1.0)  │
├──────────────────────────────────────┼───────────┼───────────────────┤
│  BYOK key lifecycle (encrypt/TTL/shred)│  ✅ Strong │  unchanged         │
│  Secret redaction (logs + 422 response)│  ✅ Strong │  ↑ 422-scrub added │
│  Multi-provider key redaction         │  ✅ Strong │  NEW               │
│  Shared seam as a typed package       │  ✅ Strong │  NEW (wegofwd-llm) │
│  Provider quirks as capabilities      │  ✅ Strong │  NEW (clamp fix)   │
│  Validate→repair (vs blind retry)     │  ✅ Strong │  NEW               │
│  Vendoring with recorded provenance   │  ✅ Strong │  unchanged         │
│  Idempotency + bounded retry          │  ✅ Strong │  unchanged         │
│  Runtime isolation (compiler subproc) │  ✅ Strong │  unchanged         │
│  ADR decision discipline              │  ✅ Strong │  6 → 13 ADRs       │
│  Config fail-fast / no secret defaults│  ✅ Good   │  unchanged         │
│  Seam version-pin currency            │  ⚠️ Weak   │  NEW (pins v0.1.0; │
│                                       │           │  pkg at v0.1.1)    │
│  Dependency sourcing (git vs registry)│  ⚠️ Weak   │  NEW (git+https)   │
│  Durable job execution                │  ⚠️ Weak   │  in-proc BG task   │
│  Spec ↔ code frame reconciliation     │  ⚠️ Weak   │  half-fixed        │
│  Public-surface hardening (CORS/RL)   │  ⚠️ Weak   │  unchanged         │
│  Deployed + on-device test coverage   │  ⚠️ Gap    │  still not run     │
└──────────────────────────────────────┴───────────┴───────────────────┘
```

The shape is consistent and still telling: **everything that protects the user's key is strong — and got stronger (the 422-scrub fix)**; the seam extraction is a genuine architecture-quality win; and the weak items are all the same family — MVP deferrals (jobs/CORS/auth) plus *reconciliation debt* that now spans repos (version pins) as well as docs. None are architectural mistakes; all are cheap to close.

---

*Practices observed in the code on disk at `40166ee` (branch `main`), the `wegofwd-llm` package (latest tag `v0.1.1`), and `pramana` (HEAD `e2958ef`, branch `feat/ai-drafted-approved-content` — a cross-repo grep confirms Pramana does not yet import the seam). Where docstrings, `MVP_v1.md`, or `docs/STATUS.md` disagreed with the implementation, the implementation was treated as the source of truth. `pytest` was not runnable in the review environment, so test-pass claims rest on reading the asserting tests, not a green run. Supersedes v1.0 (2026-06-02 @ `e1c66f7`).*
