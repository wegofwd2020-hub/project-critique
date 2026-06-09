# StudyBuddy SelfLearner (Mentible) — Code Review & Critique

**Reviewed:** 2026-06-09 (v2.0 — major refresh; measured on disk at branch `main` @ `40166ee`. **97 commits since v1.0**; headline shifts: LLM provider seam extracted into the installable `wegofwd-llm` package (ADR-012), Pramana in-process generation integration (ADR-011/013), multi-provider BYOK with free providers, BYOK 422-scrub security fix (ADR-001).)
**Prior review:** 2026-06-02 (v1.0 — first review, branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`)
**Repo:** `wegofwd2020-hub/StudyBuddy_SelfLearner` · **Public brand:** **Mentible** (tagline *"Author Yourself"*; ADR-006, name pending trademark/domain clearance — formerly "StudyBuddy Q")
**Phase:** Pre-deploy MVP — feature-complete in code for a now-larger MVP slice (multi-provider, books-only), **still not yet verified against a deployed backend**; some provider paths *are* now self-reported as live-verified (Groq/Anthropic) per commit messages
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## What changed since v1.0 (the 97-commit window)

Between `e1c66f7` (2026-06-02) and `40166ee` (2026-06-09), the project landed 97 commits (228 total; first commit 2026-04-25) and grew from 6 ADRs to **13**. Four architectural shifts dominate, all on `main` now:

1. **The LLM provider seam was extracted into an installable package — `wegofwd-llm` (ADR-012).** What was an inlined, per-provider provider layer is now a standalone repo (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/wegofwd-llm`, **773 LOC src / 48 tests**, tags `v0.1.0`/`v0.1.1`). SelfLearner now consumes it as a dependency: `backend/requirements.txt` pulls `wegofwd-llm[anthropic] @ git+https://github.com/.../wegofwd-llm@v0.1.0`, and the backend imports `wegofwd_llm.{conformance,contract,errors,registry}` directly (`tasks.py`, `anthropic_caller.py`, `schemas.py`). ADR-012 frames the package as serving the *whole product family* (Mentible + Pramana), but **on disk the only consumer is Mentible** — a definitive grep across all three repos shows zero `wegofwd_llm` imports in the Pramana checkout (HEAD `e2958ef`, 2026-06-07). So this is real DRY-by-design with one realized consumer today; the cross-repo coupling risk (git-pin versioning, no registry) is real now, the multi-consumer DRY payoff is still pending Pramana actually wiring the seam.

2. **Multi-provider BYOK with free providers (ADR-005 → built).** ADR-005 was "accepted but unbuilt" in v1.0; it is now implemented across 5 phases. The seam ships Anthropic (native tool-use), OpenAI-compatible, and **free providers** Groq / OpenRouter / Gemini. Provider + model are a per-book `GenerationParam`; the mobile keystore is now **multi-provider** (`mobile/src/secure/keyStore.ts` — per-provider namespaced SecureStore keys); generation provenance (provider/model/fingerprint) is persisted on the saved unit. The blind-retry loop was replaced with a **validate→repair conformance loop** (`generate_validated`).

3. **Pramana compliance/generation integration (ADR-011 *Proposed*, ADR-013 *Accepted* — both Mentible-side ADRs).** Pramana (`.../STEM_studybuddy/pramana`, HEAD `e2958ef`, branch `feat/ai-drafted-approved-content`) is a separate compliance/publication system. The on-disk integration is an **HTTP artifact-exchange seam**, *not* a shared code dependency: `pramana/services/mentible_client.py` pushes a "Package Request" outbound to Mentible and `consumer_library.py` ingests the signed Consumable Package inbound (ADR-011's "consumable handoff"; the module is explicitly a thin port — payload fixed, URL/auth not yet specified, default `NullMentibleClient` for dev). ADR-013 ("Pramana in-process generation") is a decision document **in Mentible's `docs/adr/`** (Mentible commit `78df7f4`) drawing the boundary — the **artifact** is the line, not the act of calling an LLM — but Pramana's checked-out code has **not** wired in-process generation against the seam (zero `wegofwd_llm` imports). The boundary ADR-013 draws is sound; treat it as accepted *intent*, with Pramana's side still to be built.

4. **The BYOK 422-scrub security fix (ADR-001).** A real leak class was found and closed: FastAPI's default 422 handler echoes the offending request `input` back to the caller, and on a *missing required field* the `input` is the whole request body — **including the api_key**. A custom `RequestValidationError` handler now runs every error through `scrub_validation_errors()` (loc-based wholesale redaction for sensitive fields + value-pattern scrubbing) before returning. **Confirmed closed** (see §5).

Other notable changes: **Books-only pivot** — the standalone Query single-lesson surface was removed (ADR-009); per-provider **output-token clamping** (Groq free tier returned HTTP 413 on the fixed 16384 budget — `min()`, never a floor); book-template/theme system (ADR-007); release lifecycle & watermarking (ADR-008); opt-in **narrative/animated-character lesson mode** (ADR-010, *Proposed* — prompt-level animated-SVG path prototyped); a much-expanded compiler (house-style parity, branded diagram themes, accessibility metadata); a Mentible brand-asset rollout; and `docs/PROFESSIONAL_PUBLISHING.md` + manus.ai comparison docs.

### Re-measured numbers (v1.0 → v2.0, all from `wc -l` / `grep` on disk at `40166ee`)

| Metric | v1.0 (`e1c66f7`) | v2.0 (`40166ee`) |
|---|---|---|
| Commits (total / since prior) | 131 / — | **228 / +97** |
| ADRs | 6 | **13** |
| Backend src LOC / test LOC | 1,843 / 1,428 | **1,953 / 1,771** |
| Backend `def test_` (files) | 75 (11) | **96 (11)** |
| Pipeline LOC | 1,007 | **1,246** |
| Compiler src / test LOC | 1,631 / 927 | **2,223 / 1,048** |
| Compiler `it/test` blocks (files) | ~60 (9) | **71 (11)** |
| Mobile src / test LOC | 6,511 / 2,048 | **7,696 / 2,212** |
| Mobile `it/test` blocks (files) | ~111 (22) | **132 (23)** |
| In-repo production LOC (excl. tests) | ~10,992 | **~13,118** (mobile 7,696 / compiler 2,223 / backend 1,953 / pipeline 1,246) |
| New external seam package | — | **`wegofwd-llm` 773 LOC / 48 tests** |
| `tests/llm/` (top level) | orphan `.pyc` only | **`test_config.py` now real (15 funcs)** + residual `.pyc` |

---

## Executive Summary

Mentible remains the **direct-to-learner answer to a GTM problem**: a thin, opinionated authoring client over the scoped-query IP, sold to adults who **bring their own key (BYOK)** so the vendor never carries a token bill, compiling generated content into a portable EPUB3/PDF book. Since v1.0 it has matured along two axes — it became **books-only** (the single-lesson Query surface removed, ADR-009) and **multi-provider** (Anthropic + OpenAI-compatible + free Groq/OpenRouter/Gemini).

**The headline architectural event is the extraction of the provider seam into the installable `wegofwd-llm` package (ADR-012).** In v1.0 the multi-provider layer was an accepted-but-absent ADR and `tests/llm/` held only orphan `.pyc` files. It is now real code, in its own repo, with a typed contract (`LLMRequest`/`LLMResponse`/`Provider`), a registry, a validate→repair conformance loop, and 48 of its own tests. ADR-012 frames it as serving the whole product family, and that is the right move (package the seam, don't fork it three ways) — but the honest on-disk state is **one realized consumer (Mentible)**; the Pramana checkout imports nothing from it. The cost is **new cross-repo coupling**: the dependency is a **git URL pinned to a tag** (`@v0.1.0`), not a package on any registry, so CI and every install build it over the network from GitHub; and the pin has *already drifted* — SelfLearner pins `v0.1.0` while the package itself is at `v0.1.1` (a `py.typed` packaging fix). A consumer one tag behind its dependency is low-severity today but is exactly the failure mode a shared-package seam introduces.

**The BYOK 422-scrub fix is the security highlight, and it is real.** v1.0 did not flag this leak — it was found and closed in this window. The default 422 handler would have handed the user's `sk-ant-` key straight back in an HTTP response body on a malformed-but-key-bearing request. The fix is a custom handler + `scrub_validation_errors()` that redacts both by field-name (`loc` ends in `api_key`/`authorization`) and by value-pattern, backed by an explicit test (`test_missing_field_422_does_not_echo_key`). For a product whose entire trust proposition is "we touch your key safely," catching and closing a key-echo class this subtle is exactly the discipline the product needs.

**The honest gaps are largely the same ones, plus the coupling.** The job runner is still an **in-process FastAPI `BackgroundTask`**, not the Celery/Redis queue the plan describes — a restart still loses in-flight jobs. The backend is still not deployed to a public URL (per `docs/STATUS.md`, last updated 2026-05-26). CORS, rate-limiting, auth, and queue-depth caps remain by-design MVP omissions. And the **doc-drift v1.0 flagged is only partially fixed**: `CLAUDE.md`/`SCOPE.md` got layered ADR-009/ADR-004 amendment *notes*, but the top-of-file status header still reads "Pre-MVP — directory stubs only, no application code yet," and `docs/STATUS.md` is still pinned to `feat/mobile-skeleton` / 2026-05-26, now ~140 commits stale.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Four clean layers + a now-**externalized provider seam (`wegofwd-llm`)** (one realized consumer, Mentible; family-DRY by intent); typed contract + conformance loop; new risk = cross-repo git-pin coupling (SelfLearner pins `v0.1.0`, package at `v0.1.1`) |
| Code Quality | 🟢 Strong | `mypy`/`ruff` backend, typed TS compiler, zero committed secrets, single brand constant; multi-provider keystore namespaced cleanly; conformance/repair replaces blind retry |
| Test Coverage | 🟡 Good | 96 backend `def test_` (was 75) + 71 compiler + 132 mobile blocks + 48 in the seam package; new live-provider self-reports (Groq/Anthropic) but **still no deployed-backend E2E**; residual `tests/llm/*.pyc` orphans |
| Documentation | 🟡 Good | 13 ADRs (was 6) — reasoning fully legible; but `CLAUDE.md`/`SCOPE.md` header + `STATUS.md` **still stale** (v1.0 finding only half-closed); ADR-010/011 still *Proposed* |
| Security | 🟢 Strong | BYOK Pattern B intact **+ the 422 key-echo leak found and closed (ADR-001)**; multi-provider redaction (`<redacted-provider-key>`); CORS `*` / no-auth still deferred |
| Scalability / Ops | 🟡 Good | In-process `BackgroundTask` still the ceiling; new cross-repo build dependency (git+https, no registry) is a supply/availability coupling; still undeployed |

**Top 5 actions:** (1) **Fix the `wegofwd-llm` version pin** — bump SelfLearner from `@v0.1.0` to the package's `@v0.1.1`, and decide a registry (private PyPI / GitHub Packages) so installs don't depend on a live git fetch. (2) Replace the in-process `BackgroundTask` with the planned Celery/Redis worker, or formally document the restart-data-loss window. (3) **Close the doc-drift for real** — fix the `CLAUDE.md`/`SCOPE.md` status header and refresh `docs/STATUS.md` (multi-provider, books-only, package seam, ~13k LOC); amendment notes layered over a "directory stubs only" header is not enough. (4) Deploy to Fly and run one real end-to-end BYOK generation against the deployed backend — the verification gate everything still waits on. (5) Resolve ADR-010 (narrative mode) and ADR-011 (Pramana handoff) from *Proposed* — both have prototype code ahead of a decision.

---

## What This Product Is (and Isn't)

| | StudyBuddy_OnDemand | **Mentible (this repo)** | **Pramana** |
|---|---|---|---|
| Audience | Schools, districts (K-12) | Self-motivated adult learners | Compliance/publication backend |
| Token spend | StudyBuddy pays | **User pays (BYOK, multi-provider)** | — (not yet wired to the seam) |
| Output | Rendered lessons in-app | **Compiled EPUB3 / PDF book** | Approved **consumable package** |
| LLM access | inline pipeline providers | **`wegofwd-llm` seam (sole on-disk consumer)** | none on disk (HTTP handoff to Mentible) |
| Integration | — | One-way vendor of `pipeline/` prompts; consumes the seam package | **HTTP artifact exchange** with Mentible (`mentible_client.py`, ADR-011) |

The IP shared with OnDemand is still the **six scope dimensions**. New in this window: the **provider seam is now a package** (consumed by Mentible; ADR-012 intends Pramana too, but Pramana does not yet import it), and a *Proposed* "consumable package" handoff (ADR-011) connects Mentible (authoring) to Pramana (compliance/approval) via an **HTTP artifact exchange**, not a shared code dependency.

---

## 1. Architecture

### Strengths

- **Four clean layers, now with an externalized seam.** `mobile/` → backend REST; `backend/src/{generate,structure,export}` → `core/` + `pipeline/` + **`wegofwd_llm`**; `pipeline/` providers → the seam contract. The new dependency edge points *outward* to a versioned package, not sideways into a sibling repo's source — the right direction.
- **The `wegofwd-llm` seam is genuinely well-factored.** A typed `contract.py` (`LLMRequest`/`LLMResponse`/`Provider` ABC/`Capabilities`), a `registry.py` of `ProviderSpec`s (default model + capabilities incl. `max_output_tokens` ceilings), a `conformance.py` `generate_validated` validate→repair loop, native Anthropic tool-use, and an OpenAI-compatible provider. 48 tests, `py.typed` shipped (v0.1.1). It is small (773 LOC) and does one thing.
- **Per-provider output-token clamping is a real correctness fix.** `Capabilities.max_output_tokens` (0 = uncapped) + a `min(req.max_tokens, cap)` clamp in the OpenAI-compatible provider closed a live HTTP-413 from Groq's free tier (registry: groq/openrouter = 8000, gemini = 8192; OpenAI/Anthropic uncapped). It's a `min()`, never a floor — small requests pass through. This was found by a real BYOK call on an emulator, not in theory.
- **The compiler remains a separate, key-free, deterministic runtime** (now larger and richer: house-style parity, branded diagram themes/tokens, EPUB Accessibility 1.1 OPF metadata, release watermarking).
- **Security-first design captured as decisions.** 13 ADRs; the 422-scrub fix is documented under ADR-001, the seam under ADR-012, the Mentible↔Pramana boundary under ADR-011/013.

### Gaps & Risks

⚠️ **Cross-repo coupling via a git-pinned, registry-less dependency.** `wegofwd-llm` is pulled as `git+https://github.com/.../wegofwd-llm@v0.1.0`. There is no package registry, so every CI run and every install builds it from a live GitHub fetch (availability + supply-chain surface). More concretely, **the pin already lags the package**: SelfLearner pins `v0.1.0` while the package is at `v0.1.1` (a `py.typed`/PEP 561 fix). A consumer one tag behind its own dependency is the coupling cost made manifest in week one — and it multiplies the moment Pramana becomes a second consumer. Pin to the latest tag and publish the package somewhere resolvable.

⚠️ **The job runner is still not what the architecture says it is.** `tasks.py` is honest ("Migration to Celery for v1.1 is straightforward… a process restart loses in-flight jobs"), but for minutes-long async generation an unlucky deploy still silently drops a user's in-flight job and leaves an encrypted envelope in Redis until TTL.

⚠️ **The Mentible↔Pramana integration is decided ahead of its code.** ADR-010 (narrative/animated-character mode) has a prototyped animated-SVG prompt path while still *Proposed*. ADR-011 (Mentible↔Pramana consumable handoff) is *Proposed* and is the larger architecture; ADR-013 (its in-process amendment) is *Accepted* — but on disk Pramana's side is only a thin outbound HTTP port (`mentible_client.py`, default `NullMentibleClient`, URL/auth unspecified) and Mentible has not built an inbound Package-Request endpoint. Accepted-decision-ahead-of-code on a cross-product boundary is where integration architecture drifts.

⚠️ **Single-consumer compiler contract, unchanged.** `book.json` is still the unversioned contract between backend↔compiler and OnDemand↔reader. Add a `schema_version` field and validate it.

---

## 2. Code Quality

### Strengths

- **No committed secrets, enforced.** The repo-wide `no-real-key-in-repo` CI gate still runs; multi-provider redaction now also covers non-Anthropic keys (`<redacted-provider-key>`).
- **Backend is linted and typed; the seam mirrors the same ruff config** so a file passes lint identically in either repo (per `wegofwd-llm/pyproject.toml`).
- **Conformance/repair replaces blind retry.** The worker now routes through `generate_validated` (validate the response, and on a schema miss send a targeted repair turn) rather than re-rolling the whole generation up to N times — fewer wasted tokens on the user's bill.
- **Multi-provider keystore is migration-safe.** `keyStore.ts` keeps Anthropic on the legacy storage key (`sbq_byok_key`) so existing installs need no migration, and namespaces others (`sbq_byok_key_{provider}`). Provider id matches the backend registry / `GenerationParams.provider` — one identifier across the stack.
- **Single source of brand truth** (`mobile/src/constants/brand.ts`); `app.json`/identifiers still intentionally `studybuddy-q` pending clearance.

### Gaps & Risks

⚠️ **Residual orphan bytecode.** `tests/llm/` is no longer pure orphans — `test_config.py` (15 funcs) is now real source — but `tests/llm/__pycache__/*.pyc` from *deleted* test modules (`test_conformance`, `test_registry`, `test_anthropic_native`, …) still sits committed with no matching source. Those modules now live in the `wegofwd-llm` repo; `git rm` the stale `.pyc`.

⚠️ **`max_tokens` defaults are duplicated across the seam boundary.** `16384` appears as the default in `wegofwd_llm/contract.py`, `backend/src/generate/tasks.py`, `pipeline/providers/base.py`, and `anthropic_caller.py`. With clamping now centralized in the seam, the pipeline-side legacy `16384` defaults are belt-and-suspenders at best and a drift risk at worst.

⚠️ **CPython `del api_key` still can't zero memory.** Acknowledged in code; worth the one-line note in ADR-001's threat model (the Redis copy *is* genuinely deleted; the in-process shred is best-effort).

---

## 3. Test Coverage

### Strengths

- **The security-critical path is tested first and has grown.** `test_no_key_in_logs.py` is up to 138 lines and now covers the new vectors: `test_missing_field_422_does_not_echo_key` (the 422 leak), a failed-job worker error path for Anthropic *and* OpenAI keys (the most realistic leak vector — an SDK error stringifying the key). Backend `def test_` count rose **75 → 96**.
- **The seam package is independently tested** — 48 `def test_` across `test_{allowlist,anthropic_native,conformance,openai_compatible,registry,versioning}.py`, including the 3 clamp cases (clamps down / not raised below ceiling / uncapped at 0).
- **Compiler and mobile suites grew** (compiler 71 blocks/11 files; mobile 132 blocks/23 files) tracking the new compiler/house-style and import/cover work.
- **Some provider paths are now self-reported live-verified.** Commit messages record real BYOK calls (Groq → 200, single call, schema-valid first try; Anthropic tool-use "unit-green, LIVE-UNVERIFIED" for the tool path). This is more than v1.0 had — but it is commit-message provenance, not a committed live test.

### Gaps & Risks

⚠️ **Still no deployed-backend end-to-end test.** Per `docs/STATUS.md` (stale, 2026-05-26) the backend has no public URL; no committed test exercises a deployed instance. The live-provider self-reports are encouraging but unrepeatable in CI by design (no real keys in CI).

⚠️ **No mobile on-device E2E.** The BYOK loop UX (multi-provider key load, WebView render, minutes-long poll) is still only unit-tested.

⚠️ **The seam is tested in its own repo, not here.** SelfLearner's CI installs `wegofwd-llm` from the git pin but runs none of the seam's 48 tests; a seam regression at a new tag is only caught if SelfLearner re-pins and its own tests happen to exercise the changed path.

⚠️ **JS counts are `it/test(` blocks, not asserted-unique cases** — treat 71/132 as upper-bound approximations; backend's 96 is an exact `def test_` count.

---

## 4. Documentation

### Strengths

- **13 ADRs capture every pivot** (was 6). New: ADR-007 (templates/theme, Accepted 2026-06-03), ADR-008 (release lifecycle/watermarking, Accepted 2026-06-03), ADR-009 (books-only, Accepted 2026-06-05), ADR-010 (narrative mode, *Proposed*), ADR-011 (Pramana handoff, *Proposed*), ADR-012 (shared seam package, **Accepted 2026-06-09**), ADR-013 (Pramana in-process generation, **Accepted 2026-06-09**). The reasoning is fully legible. (ADR statuses verified from the files' own `**Status:**` lines.)
- **The seam and integration decisions are documented from both sides.** ADR-012 argues "library, not a service" (D8); ADR-013 draws the artifact-not-the-LLM-call boundary between Mentible and Pramana cleanly (even though Pramana's code hasn't realized it yet).
- **`docs/PROFESSIONAL_PUBLISHING.md`** (385 lines) and the manus.ai comparison docs add real product/positioning depth.

### Gaps & Risks

⚠️ **The v1.0 doc-drift is only half-closed.** `CLAUDE.md` and `SCOPE.md` received ADR-009/ADR-004 amendment *notes*, but `CLAUDE.md`'s top-of-file status line still reads **"Pre-MVP — directory stubs only, no application code yet"** over a ~13k-LOC codebase, and `docs/STATUS.md` is still **"Last updated 2026-05-26, branch `feat/mobile-skeleton`"** — now ~140 commits stale, predating multi-provider, books-only, and the package seam entirely. A new contributor reading top-down still builds the wrong mental model before reaching the ADRs. **Fix the headers, not just append notes.**

⚠️ **`MVP_v1.md` plan still says Celery; code is still `BackgroundTask`.**

⚠️ **No `CONTRIBUTING.md` / multi-repo dev runbook** — and the multi-repo story is now more complex (SelfLearner + `wegofwd-llm` + Pramana, editable-install dance noted only in a `requirements.txt` comment).

---

## 5. Security — the headline area

### Strengths

- **BYOK Pattern B intact** (HTTPS-body key, AES-256-GCM envelope in Redis under an HKDF-per-job key, TTL + shred, structlog redaction by field-name *and* `sk-ant-` value-regex, CI key-leak gate). All unchanged and verified on disk.
- ✅ **The 422 key-echo leak is found and closed (ADR-001).** Verified by reading `backend/main.py` (a custom `@app.exception_handler(RequestValidationError)` that runs `scrub_validation_errors(exc.errors())`) and `backend/src/core/log_redaction.py:119` (`scrub_validation_errors`: loc-based wholesale redaction when the error targets a sensitive field — catching a too-short or non-`sk-ant-` key that the value-regex can't — *and* value-based `_scrub_value` otherwise). Backed by `test_no_key_in_logs.py::test_missing_field_422_does_not_echo_key`, which posts a real fake key in a body missing a required field and asserts the key is absent from `resp.text`. This is a genuine leak class (the default FastAPI 422 echoes the whole request body, which is the key on a missing-field error) and it is genuinely closed.
- **Multi-provider redaction.** The seam introduced non-Anthropic keys; `log_redaction.py` now redacts provider keys too (`<redacted-provider-key>`), and the worker error-path tests cover an OpenAI-key leak vector, not just Anthropic.

### Gaps & Risks

⚠️ **CORS `allow_origins=["*"]`, no auth, no rate-limit, no queue-depth cap** — all the v1.0 by-design MVP omissions persist; the first public deploy is still unauthenticated and unbounded over an endpoint carrying the user's key.

⚠️ **docker-compose all-zeros dev master key** — still a copy-paste-to-prod hazard; refuse to start on the all-zeros value when `APP_ENV != development`.

⚠️ **New supply-chain edge: the seam is fetched from a git URL at build time.** A compromised or unavailable `wegofwd-llm@<tag>` would break or poison every install. A registry with hash-pinning closes this.

⚠️ **In-process worker still holds the encrypted envelope through a restart window** (encryption keeps it low-severity; the durable-queue migration closes it cleanly).

---

## 6. Scalability / Operability

### Strengths

- **Scale-to-zero Fly config remains deploy-ready**; `/readyz` checks Redis; the heavy compile work stays isolated in the subprocess compiler.
- **The conformance/repair loop reduces wasted token spend** under schema-miss conditions (fewer full re-rolls), which is both a cost and a latency win on the user's bill.

### Gaps & Risks

⚠️ **In-process `BackgroundTask` is still the scaling ceiling** — one process, one worker pool, no restart durability.

⚠️ **No load/perf data; the compile step (headless Chromium/Vivliostyle) is still the untested tail-latency risk**, now with more compiler features (watermarking, theming) on the path.

⚠️ **Still not deployed** — no public URL, APK not built (per stale STATUS.md). Everything operational remains theoretical until the first Fly deploy + device run.

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P1 | **Reconcile the `wegofwd-llm` version pin** (SelfLearner `@v0.1.0` lags the package's `@v0.1.1`) and publish the seam to a resolvable registry so installs don't depend on a live git fetch | Architecture / Supply chain |
| P1 | Deploy backend to Fly + run one real BYOK generation against the deployed backend — the single gate everything else waits on | Verification |
| P1 | Replace in-process `BackgroundTask` with Celery/Redis, or explicitly document the restart-data-loss window as accepted for MVP | Architecture |
| P1 | **Actually fix the stale headers** in `CLAUDE.md`/`SCOPE.md` and refresh `docs/STATUS.md` (multi-provider, books-only, seam package, ~13k LOC) — amendment notes over a "directory stubs only" header isn't enough | Documentation |
| P1 | Lock CORS off `*`, add rate-limiting + queue-depth cap, refuse the all-zeros master key outside dev — before any public URL | Security |
| P2 | Decide ADR-010 (narrative mode) and ADR-011 (Pramana handoff) from *Proposed* — both have prototype code ahead of the decision | Architecture |
| P2 | Pin + version the `book.json` schema and validate it on both boundaries | Architecture |
| P2 | Add on-device (Detox/Maestro) E2E for the multi-provider BYOK loop, and a committed live-provider smoke test gated on an opt-in secret | Testing |
| P2 | De-duplicate the `16384` `max_tokens` defaults now that clamping lives in the seam | Code Quality |
| P3 | `git rm` the stale `tests/llm/__pycache__/*.pyc` orphans (the modules moved to `wegofwd-llm`) | Code Quality |
| P3 | Add a `CONTRIBUTING.md` / multi-repo dev runbook (SelfLearner + `wegofwd-llm` + Pramana, editable installs) | Documentation |
| P3 | Note in ADR-001's threat model that the in-process `del api_key` shred is best-effort | Security |

---

*This critique is a point-in-time review measured against the code on disk at `40166ee` (branch `main`, 2026-06-09), the 13 ADRs, the commit log `e1c66f7..HEAD` (97 commits), and the sibling repos `wegofwd-llm` (latest tag `v0.1.1`) and `pramana` (HEAD `e2958ef`, branch `feat/ai-drafted-approved-content`). Deployment status and on-device UX are **self-reported in `docs/STATUS.md`** (now stale) and were not verifiable from source; pytest could not be executed in the review environment (no `pytest` module installed), so the 422-scrub claim is verified by reading the handler, the `scrub_validation_errors` implementation, and the asserting test, not by a green run. The brand "Mentible" is adopted per ADR-006 pending trademark/domain clearance; the repo and some identifiers remain `StudyBuddy_SelfLearner` / `studybuddy-q` intentionally. Supersedes v1.0 (2026-06-02 @ `e1c66f7`).*
