# Mentible — Code Review & Critique

**Reviewed:** 2026-06-09 (v2.0 — major refresh; measured on disk at branch `main` @ `40166ee`. **97 commits since v1.0**; headline shifts: LLM provider seam extracted into the installable `wegofwd-llm` package (ADR-012), Pramana in-process generation integration (ADR-011/013), multi-provider BYOK with free providers, BYOK 422-scrub security fix (ADR-001).)
**Addendum:** 2026-07-14 — **the AI-capability expansion (ADR-028 → ADR-032)**, measured at `main@28a62c8` (**677 commits**, +135 since 2026-07-06). Open Shelves is **built**; ADR-029/030/032 are **paper**; **ADR-032 amends ADR-001 (no server-side key custody)** and reverses ADR-028's device-local promise in its own words. See the §1 and §5 updates, the new P0s, and the companion diagram [`mentible_enhanced_features_mindmap.drawio`](mentible_enhanced_features_mindmap.drawio).
**Prior review:** 2026-06-02 (v1.0 — first review, branch `feat/authoring-regenerate-export-fixes` @ `e1c66f7`)
**Repo:** `wegofwd2020-hub/Mentible` · **Public brand:** **Mentible** (tagline *"Author Yourself"*; ADR-006, name pending trademark/domain clearance — formerly "StudyBuddy Q", earlier "StudyBuddy SelfLearner")
**Phase:** ~~Pre-deploy MVP~~ → **SHIPPED.** As of the 2026-07-14 addendum, Mentible is **live in production**: backend at `mambakkam.net/mentible-api` (Hetzner VPS), full web app at `/app/mentible`, public demo at `/demos/mentible`, **Android APK released**, **`v0.2.0` tagged 2026-06-28**. *The v2.0 body below was written pre-deploy and describes a pre-deploy product; several of its findings are now closed and one has **escalated** — see **"Corrections"** immediately below before reading further.*
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Corrections — 2026-07-14: what the v2.0 body gets wrong now

**The v2.0 review (2026-06-09, `40166ee`) was accurate when written and is stale now.** Mentible shipped. Read these corrections before trusting any deployment, documentation, or supply-chain claim in the sections below — this review told readers Mentible was pre-deploy, and that is **false**.

**Closed — the v2.0 findings that go-live and the intervening 449 commits resolved:**

| v2.0 finding | Status now | Evidence (`main@28a62c8`) |
|---|---|---|
| "**Still not deployed** — no public URL, APK not built" (§6, P1) | ✅ **CLOSED** | `docs/STATUS.md:130` — prod backend live at `mambakkam.net/mentible-api` (Hetzner VPS, `docker-compose.demo.yml`, behind host nginx); full web app `/app/mentible`; demo `/demos/mentible`; **Android APK released**; `v0.2.0` tagged 2026-06-28 |
| "Deploy to **Fly** + run one real BYOK generation" (P1) | ✅ **OBSOLETE** | It shipped on **Hetzner**, not Fly. `fly.toml` (`app = "studybuddyq-backend"`) is now **vestigial** — remove it or note it as dead, since it misleads on the real deploy target |
| "`wegofwd-llm` **pin lags** (`@v0.1.0` vs package `@v0.1.1`)" (P1) | ✅ **CLOSED** | `backend/requirements.txt:35` — now `@v0.2.0` (the `trust` submodule the Content Trust code imports) |
| "**Doc-drift**: `CLAUDE.md` still says 'Pre-MVP — directory stubs only'; `STATUS.md` ~140 commits stale at 2026-05-26" (§4, P1) | ✅ **CLOSED** | `CLAUDE.md` header rewritten (brand/repo/ADR-006); `docs/STATUS.md` current to **2026-07-03**. The header fix this review demanded was made |
| "Residual orphan `tests/llm/__pycache__/*.pyc`" (§2, P3) | ✅ **CLOSED** | Directory no longer exists |
| "Backend not verified against a deployed instance" (§3) | ✅ **CLOSED** | Super-admin suspend→audit→reactivate→delete **"verified on prod"** (`STATUS.md`) |

❌ **ESCALATED — the one that got worse.** §5 flagged `allow_origins=["*"]`, no auth, no rate-limit as *"by-design MVP omissions… before any public URL."* **The public URL now exists, and `backend/main.py:80` still reads `allow_origins=["*"]`.** The precondition attached to that finding has been crossed without the finding being addressed. On a **live** backend whose request bodies carry the user's BYOK API key, wildcard CORS means **any origin can drive a cross-origin request against the API**. Supabase JWKS auth and a per-IP limiter (`core/rate_limit.py`) now exist and blunt the worst of it, but the wildcard itself is unchanged and is no longer a pre-launch note — **it is a production configuration**. This is now the **highest-severity open item in the document.**

**Still open (v2.0 findings that survive):** the job runner is still an in-process `BackgroundTask`, not Celery (`backend/src/generate/tasks.py`); `book.json` still has **no `schema_version`** (grep: zero hits across `backend/src` and `compiler/src`); **ADR-010 and ADR-011 are still *Proposed*** ("awaiting decision", 2026-06-05) — 39 days and ~450 commits later; no guard was found in `backend/config.py` refusing the all-zeros dev master key outside development.

**New since v2.0, undocumented in the body:** a second shared-package dependency, **`wegofwd-secure @ v0.1.0`** (`backend/requirements.txt:42`), which inherits the same git-pin/no-registry supply-chain posture §1 flags for `wegofwd-llm` — now doubled.

**Process note.** This review's own §4 hammered the project for stale status headers while its own header sat five weeks stale, telling readers a shipped product was pre-deploy. The project fixed its drift faster than the critique did. A point-in-time review that is not re-dated becomes exactly the artifact it criticizes — so the header now carries the correction, and the diagram-drift item in the new Priority Actions block is the same disease in a third surface.

---

## What changed since v1.0 (the 97-commit window)

Between `e1c66f7` (2026-06-02) and `40166ee` (2026-06-09), the project landed 97 commits (228 total; first commit 2026-04-25) and grew from 6 ADRs to **13**. Four architectural shifts dominate, all on `main` now:

1. **The LLM provider seam was extracted into an installable package — `wegofwd-llm` (ADR-012).** What was an inlined, per-provider provider layer is now a standalone repo (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/wegofwd-llm`, **773 LOC src / 48 tests**, tags `v0.1.0`/`v0.1.1`). Mentible now consumes it as a dependency: `backend/requirements.txt` pulls `wegofwd-llm[anthropic] @ git+https://github.com/.../wegofwd-llm@v0.1.0`, and the backend imports `wegofwd_llm.{conformance,contract,errors,registry}` directly (`tasks.py`, `anthropic_caller.py`, `schemas.py`). ADR-012 frames the package as serving the *whole product family* (Mentible + Pramana), but **on disk the only consumer is Mentible** — a definitive grep across all three repos shows zero `wegofwd_llm` imports in the Pramana checkout (HEAD `e2958ef`, 2026-06-07). So this is real DRY-by-design with one realized consumer today; the cross-repo coupling risk (git-pin versioning, no registry) is real now, the multi-consumer DRY payoff is still pending Pramana actually wiring the seam.

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

**The headline architectural event is the extraction of the provider seam into the installable `wegofwd-llm` package (ADR-012).** In v1.0 the multi-provider layer was an accepted-but-absent ADR and `tests/llm/` held only orphan `.pyc` files. It is now real code, in its own repo, with a typed contract (`LLMRequest`/`LLMResponse`/`Provider`), a registry, a validate→repair conformance loop, and 48 of its own tests. ADR-012 frames it as serving the whole product family, and that is the right move (package the seam, don't fork it three ways) — but the honest on-disk state is **one realized consumer (Mentible)**; the Pramana checkout imports nothing from it. The cost is **new cross-repo coupling**: the dependency is a **git URL pinned to a tag** (`@v0.1.0`), not a package on any registry, so CI and every install build it over the network from GitHub; and the pin has *already drifted* — Mentible pins `v0.1.0` while the package itself is at `v0.1.1` (a `py.typed` packaging fix). A consumer one tag behind its dependency is low-severity today but is exactly the failure mode a shared-package seam introduces.

**The BYOK 422-scrub fix is the security highlight, and it is real.** v1.0 did not flag this leak — it was found and closed in this window. The default 422 handler would have handed the user's `sk-ant-` key straight back in an HTTP response body on a malformed-but-key-bearing request. The fix is a custom handler + `scrub_validation_errors()` that redacts both by field-name (`loc` ends in `api_key`/`authorization`) and by value-pattern, backed by an explicit test (`test_missing_field_422_does_not_echo_key`). For a product whose entire trust proposition is "we touch your key safely," catching and closing a key-echo class this subtle is exactly the discipline the product needs.

**The honest gaps are largely the same ones, plus the coupling.** The job runner is still an **in-process FastAPI `BackgroundTask`**, not the Celery/Redis queue the plan describes — a restart still loses in-flight jobs. ~~The backend is still not deployed to a public URL (per `docs/STATUS.md`, last updated 2026-05-26).~~ CORS, rate-limiting, auth, and queue-depth caps remain by-design MVP omissions. And the **doc-drift v1.0 flagged is only partially fixed**: ~~`CLAUDE.md`/`SCOPE.md` got layered ADR-009/ADR-004 amendment *notes*, but the top-of-file status header still reads "Pre-MVP — directory stubs only, no application code yet," and `docs/STATUS.md` is still pinned to `feat/mobile-skeleton` / 2026-05-26, now ~140 commits stale.~~

> ⚠️ **Corrected 2026-07-14 — the two struck claims above are false as of `main@28a62c8`.** The backend **is deployed** (prod live on Hetzner, APK released, `v0.2.0` tagged) and the **doc-drift is fixed** (`CLAUDE.md` header rewritten, `STATUS.md` current to 2026-07-03). The CORS/auth/rate-limit sentence, however, **has escalated rather than aged**: those omissions were excused as pre-launch, and launch happened with `allow_origins=["*"]` intact. See **Corrections** above.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Four clean layers + a now-**externalized provider seam (`wegofwd-llm`)** (one realized consumer, Mentible; family-DRY by intent); typed contract + conformance loop; new risk = cross-repo git-pin coupling (Mentible pins `v0.1.0`, package at `v0.1.1`) |
| Code Quality | 🟢 Strong | `mypy`/`ruff` backend, typed TS compiler, zero committed secrets, single brand constant; multi-provider keystore namespaced cleanly; conformance/repair replaces blind retry |
| Test Coverage | 🟡 Good | 96 backend `def test_` (was 75) + 71 compiler + 132 mobile blocks + 48 in the seam package; new live-provider self-reports (Groq/Anthropic) but **still no deployed-backend E2E**; residual `tests/llm/*.pyc` orphans |
| Documentation | 🟡 Good | 13 ADRs (was 6) — reasoning fully legible; but `CLAUDE.md`/`SCOPE.md` header + `STATUS.md` **still stale** (v1.0 finding only half-closed); ADR-010/011 still *Proposed* |
| Security | 🟢 Strong | BYOK Pattern B intact **+ the 422 key-echo leak found and closed (ADR-001)**; multi-provider redaction (`<redacted-provider-key>`); CORS `*` / no-auth still deferred |
| Scalability / Ops | 🟡 Good | In-process `BackgroundTask` still the ceiling; new cross-repo build dependency (git+https, no registry) is a supply/availability coupling; still undeployed |

**Top 5 actions (as written 2026-06-09 — three are now closed; see Corrections):** ~~(1) **Fix the `wegofwd-llm` version pin**~~ ✅ *(now `@v0.2.0`; the registry gap stands and has doubled with `wegofwd-secure`)*. (2) Replace the in-process `BackgroundTask` with the planned Celery/Redis worker, or formally document the restart-data-loss window — **still open, and now running in production**. ~~(3) **Close the doc-drift for real**~~ ✅ *(headers fixed; `STATUS.md` current)*. ~~(4) Deploy to Fly~~ ✅ *(shipped — on **Hetzner**, not Fly)*. (5) Resolve ADR-010 (narrative mode) and ADR-011 (Pramana handoff) from *Proposed* — **still open 39 days later**, and the *Proposed* backlog has since grown to seven ADRs.

**The current top action is neither of these:** lock **CORS off `*`** on the now-live backend (`main.py:80`), then put a real number on the **spend ceiling** that ships at `default=0`. See the 2026-07-14 Priority Actions block.

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

⚠️ **Cross-repo coupling via a git-pinned, registry-less dependency.** `wegofwd-llm` is pulled as `git+https://github.com/.../wegofwd-llm@v0.1.0`. There is no package registry, so every CI run and every install builds it from a live GitHub fetch (availability + supply-chain surface). More concretely, **the pin already lags the package**: Mentible pins `v0.1.0` while the package is at `v0.1.1` (a `py.typed`/PEP 561 fix). A consumer one tag behind its own dependency is the coupling cost made manifest in week one — and it multiplies the moment Pramana becomes a second consumer. Pin to the latest tag and publish the package somewhere resolvable.

⚠️ **The job runner is still not what the architecture says it is.** `tasks.py` is honest ("Migration to Celery for v1.1 is straightforward… a process restart loses in-flight jobs"), but for minutes-long async generation an unlucky deploy still silently drops a user's in-flight job and leaves an encrypted envelope in Redis until TTL.

⚠️ **The Mentible↔Pramana integration is decided ahead of its code.** ADR-010 (narrative/animated-character mode) has a prototyped animated-SVG prompt path while still *Proposed*. ADR-011 (Mentible↔Pramana consumable handoff) is *Proposed* and is the larger architecture; ADR-013 (its in-process amendment) is *Accepted* — but on disk Pramana's side is only a thin outbound HTTP port (`mentible_client.py`, default `NullMentibleClient`, URL/auth unspecified) and Mentible has not built an inbound Package-Request endpoint. Accepted-decision-ahead-of-code on a cross-product boundary is where integration architecture drifts.

⚠️ **Single-consumer compiler contract, unchanged.** `book.json` is still the unversioned contract between backend↔compiler and OnDemand↔reader. Add a `schema_version` field and validate it.

### Update — 2026-07-06: a second shared-package seam, *prepped but deliberately not extracted* (Help System, `main@c67b2da`)

- **The Help feature was split into an engine + content seam** (`mobile/src/help/` = product-agnostic schema/search/coverage + `HelpButton`/`HelpHint`/`HelpTopicView` render components; `mobile/src/help-content/` = Mentible's `FEATURES`/`HELP_TOPICS`/provider defs), mirroring a future `wegofwd-help` package (PR #280). The engine imports **no content** (verified across all `src/help/` files); the schema is genericized (`href`/`step`/`featureKey` → `string`) with the screen re-asserting real types via `as Href`/`as StepId` casts. Pure refactor, 408/408 mobile tests + whole-app `tsc` green — a genuinely clean boundary.
- **The discipline that governs it is the more interesting artifact.** Unlike `wegofwd-llm` (extracted on a real second consumer), `wegofwd-help` is **held in-repo per ADR-019's "extract on the real second consumer; no speculative package."** When asked to adopt Help in the two named sibling consumers (kathai-chithiram, pramana), the investigation found **both are Python back-ends with no UI** and therefore *cannot* render an RN/web help engine — so extraction was **correctly deferred**, not forced. This is the mirror image of the `wegofwd-llm` coupling risk flagged in §1 Gaps: there, a real second consumer (Pramana) *multiplies* the git-pin cost; here, the absence of a real second consumer is what (rightly) keeps the package from being born. The team applied its own ADR discipline against its own first instinct — a good sign.

⚠️ **Watch: a prepped-but-unextracted seam can rot.** `src/help/` now carries forward-looking "future `wegofwd-help`" comments and a genericized schema whose type-safety it *loses at the engine layer* (a typo'd route in content compiles, failing only at runtime — the screen casts paper over it). That cost is paid **now** for a package that may not exist for months. If a real UI second consumer never materializes, revisit whether the genericization earns its keep or should re-narrow to Mentible's own types.

### Update — 2026-07-14: the AI-capability expansion (ADR-028 → ADR-032) — one shipped, four on paper, and a **thesis reversal** (`main@28a62c8`)

**Companion diagram:** [`mentible_enhanced_features_mindmap.drawio`](mentible_enhanced_features_mindmap.drawio) — the enhancement scope as of 2026-07-10. **Read it as a snapshot, not a status board:** it labels ADR-029/030 as "candidates" (both are now real *Proposed* ADRs) and predates **ADR-031 and ADR-032 entirely**, and it marks Open Shelves "planned" when the feature is substantially **built**. The diagram's own structure is still right; its status markers have already drifted — which is itself the §4 doc-drift finding recurring in a new surface.

Mentible has moved fast since the 2026-07-06 pass: **677 commits total** (was 228 at v2.0 `40166ee`), **135 of them since 2026-07-06**, and **five new ADRs (028–032)**, all *Proposed*, dated 2026-07-10 → 2026-07-12 with an ADR-032 amendment on 2026-07-14. They are not five independent features; they are one chain, and the chain bends the product's founding thesis.

**What is actually built (verified on disk, not inferred from the ADR):**

- ✅ **Open Shelves (ADR-028) is real code, not a plan.** Backend `backend/src/shelves/` (271 LOC: `router.py` 61, `feed_fetch.py` 123, `url_guard.py` 87) exposes an anonymous, metadata-only `GET /api/v1/shelves/feed` (`router.py:45`, mounted `main.py:111`); mobile `mobile/src/openshelves/` is a **17-module** OPDS client (`opds12.ts` adapter, `downloadEngine`/`downloadIO`/`downloadTarget`, `feedSourcesStore`, `useFeedBrowser`, `ShelfFilterBar`/`shelfPrefsStore`, …) with **17 test files**, plus screens `mobile/app/(tabs)/shelves.tsx` and `mobile/app/shelves/downloads.tsx`. **30 `def test_` across four backend shelves test files.**
- ✅ **The security work went in *with* the feature, not after it.** The web feed path ships an **SSRF guard** (`url_guard.py` — resolve-then-check, literal-IP short-circuit, CGNAT blocked), a **fail-closed per-IP rate limiter**, a **manual-redirect re-validation + content-type allowlist** capped fetcher, and `Authorization`/`Cookie` stripping **on every hop**. For a feature whose whole job is "fetch a URL the user gave us," that is the right threat model, built at feature time. ADR-028 D2 was then *amended* to settle that a metadata fetch is **not a content proxy** — *"**No caching**, which is what keeps this inside D2 rather than a reversal of it."* The decision was tightened by the implementation, which is the healthy direction.
- 🟡 **The managed-access substrate (ADR-031) is ~85% pre-existing and 0% net-new.** `backend/src/billing/` is **745 LOC** (`plans`, `access`, `eligibility`, `entitlement_repo`, `usage_repo`, `pricing`, `vault`, `revenuecat`, `router`), `admin/router.py:206` already exposes `PUT /users/{sub}/entitlement`, and `alembic/0006_entitlement.py` is migrated. But ADR-031's **one net-new axis — `Plan.features`, feature entitlements — does not exist**: `billing/plans.py:20-25` has exactly `id, display, allowance_micros, managed_providers, window_days`. No `features`, no `has_feature`. **EPUB/PDF export, the first thing D4 exists to gate, is therefore ungated.**
- ❌ **ADR-029, ADR-030, and ADR-032 are entirely paper.** A word-boundary grep for `rag|embedding|vector_store|fts5|full-text-search|watch_manifest|currency_agent` across `backend/src`, `mobile/src`, `pipeline`, `compiler` returns **zero hits**. (The `staleness` symbols that *do* exist — `mobile/src/lib/staleness.ts`, `TrustBadge.tsx:235` — are the pre-existing ADR-016 staleness *hint*, which is precisely the "partial feature with no engine behind it" that ADR-030's own Context describes. Not the agent.) **Three of five ADRs are decisions with no code.**

⚠️ **ADR-032 reverses the product's founding architecture, and says so in its own words.** It states the change "is a **reversal of ADR-028's core promise**, not a tuning of ADR-029," and its header lists what it amends: **ADR-028 D2/D3/D6** (device-local / per-device / neutral-conduit / preferences-not-profiles), **ADR-014 D8** (data-minimization, device-local default — "the hosted tier holds readable content"), and, most consequentially, **ADR-001 — *no server-side key custody*** — because "the hosted tier's RAG runs on **managed** keys, never a user's." It **reshapes ADR-029 and ADR-030 into dual-mode**.

**Mentible's entire GTM and security thesis was BYOK: the vendor never holds a key, and never carries a token bill.** A hosted RAG on managed keys means the vendor now does both. That may be the right product call — device-local RAG on a phone genuinely does pressure storage and chain the user to one device, which is the honest motivation the ADR gives. But it must be named for what it is: **the moat (device-local, key-free, zero-token-liability) is being traded for a hosted tier**, and *every §5 Security guarantee in this document was written against the old posture.* This critique's security section is downstream of ADR-001; **ADR-032 amends ADR-001.**

❌ **The 2026-07-14 amendment (D11–D15) de-risks the legal exposure and, in the same stroke, puts the vendor's token bill in front of users who have paid nothing.** The de-risking is genuinely good: **D11** removes personal uploads from server scope entirely ("personal uploads never leave the device"), shrinking "the DMCA surface … to near zero — we host only works nobody owns"; **D12** anchors trust in the *source*, not the file's claim (*"**A pirated EPUB can simply assert `Rights: Public domain`**"*); **D13** makes the PD corpus shared/global/deduplicated; **D14** forbids accepting book bytes from a client at all, naming the **corpus-poisoning** vector explicitly (injected copyrighted text, or content "**crafted to steer other users' generations**"). This is careful work.

But **D15 then un-gates retrieval over that corpus from the paid tier**, and the ADR concedes the consequence in its own text:

> *"**This breaks D10's abuse argument** ('the hosted tier is paid, which structurally blunts Sybil/abuse'). Free-tier retrieval must therefore carry its own controls… Query embeddings are tiny, but they are **our** managed-key spend on a **free** user."*

And **D14's ingestion is demand-driven but server-executed** — a free user importing an un-ingested Gutenberg book causes **the server** to fetch and embed an entire book **on managed keys**. The ADR frames the economics correctly (cost collapses from once-per-user-per-book to once-per-book-ever), but it remains an **unbounded, free-user-triggered write to the vendor's token bill.** The named mitigations are "per-account rate limits + a query ceiling" — **with no figure anywhere in the ADR.**

❌ **The one backstop all of this leans on is shipping disabled.** ADR-031 D3/D8, ADR-032 D10 and ADR-032 D15 *each* cite the per-account spend ceiling as the control that makes the risk acceptable. On disk: `backend/config.py` — `managed_account_spend_ceiling_micros: int = Field(default=0)`, **`0` ⇒ no ceiling**. (Also `managed_plan_emails: str = Field(default="")` ⇒ nobody is managed-eligible today, which is the only reason this is not yet live.) **Three separate ADRs rest their abuse and cost argument on a limiter that is currently off by default.** Set a real ceiling *before* the allowlist is ever non-empty — that ordering is the whole safety margin.

⚠️ **The chain is not serialized behind managed billing — and the one part that escapes the gate is the risky part.** ADR-032 **D9** gates the *paid* hosted tier on the managed-billing launch, and ADR-030's scheduled watch was already gated there. It is tempting to conclude everything is safely queued behind one switch. **It is not: D15 deliberately exempts free-tier PD grounding from that gate.** So the shipping order is:

- **Gated** (safe to defer): paid hosted tier, cross-device sync, dual-mode RAG's hosted half, scheduled currency watch.
- **Not gated** (can ship any time, on managed keys, to free users): **PD-corpus ingestion + retrieval.**

The mind-map's purple impact edges draw the *dependency* structure correctly, but they cannot show which edges are load-bearing gates and which have been amended into no-ops. **The single un-gated edge is the one carrying the new token liability.**

⚠️ **ADR-032 has already drifted from itself.** The D11–D15 amendment was appended without reconciling the document's tail, so ADR-032 now contradicts its own text in at least four places: its **Scope** block still reads *"PD + user-own-uploads only"* and *"Not shippable before managed billing"* (falsified by D11 and D15 respectively); its **staged plan** and ticket `SBQ-HOST-002` still say *"PD-works + user-upload ingestion"*; `SBQ-HOST-005` still gates on a ToS rights-representation clause **D11 declared "no longer needed"**; and the **Consequences** block still claims a GDPR footprint over *"readable user content"* that D11 supposedly eliminated. **ADR-029 has the same disease** — its header now says "dual-mode / hosted," while its untouched *"Scope — what this ADR is not"* block still promises *"**Not** cloud retrieval — no server-side index, corpus, or query log; queries and interests never leave the device."* **The ADRs are the one artifact this project has consistently gotten right; do not let them acquire the doc-drift the rest of §4 is about.**

⚠️ **The unresolved question is the biggest one, and it is marked "not resolved here."** ADR-032 **OQ-A1**: D2's original scope was PD downloads + user uploads + **Mentible-authored books**. D11 removed uploads but is **silent on the authored books** — the user's own manuscript. If those go to the server, then server-side RAG runs over the user's unpublished work, which D6 concedes **"cannot be zero-knowledge."** That is the deepest cut into ADR-014 in the entire set, and it is currently an open owner decision inside an ADR presented as *resolving* the open decisions. Related, **OQ-A3**: a retrieval query names the book IDs to search, "so the backend learns what a user is writing against… it **partially erodes ADR-028 D6 ('preferences, not profiles')** for free-tier users, **who previously gave us nothing**."

⚠️ **And the ADR is asking, in its own text, whether the tier it exists to create still has a reason to exist.** **OQ-A4**: *"With uploads device-local (D11) and the PD corpus free (D15), the hosted tier's value is narrowed to hosting/syncing the user's **own** material. Worth re-checking that it still justifies its price and its D7 legal burden."* **A paid tier whose value proposition has been amended away twice, and whose abuse argument its own author calls broken, should be re-justified before it is built** — not after.

⚠️ **Seven *Proposed* ADRs, zero *Accepted*, three with no code — and one shipped anyway.** v2.0 flagged ADR-010/011 as prototype-ahead-of-decision; that portfolio has **grown, not shrunk** (010, 011, and now 028–032, all *Proposed*). The two failure modes now sit side by side. **ADR-028 shipped while still "Proposed"** — ~30 source files and ~20 test files merged under a decision nobody has marked Accepted, which means the *Proposed* status now carries **no information** about whether 029–032 will be built. Meanwhile **029/030/032 are a self-amending paper stack**: ADR-032 reshapes 029 and 030 before either has a line of code, then amends *itself* two days later. Paper is the cheap place to be wrong — that is the point of an ADR — but a five-deep chain of mutually-amending *Proposed* decisions with no implementation is exactly where architecture drifts from what eventually gets built. **Mark ADR-028 Accepted (the code is merged). Decide ADR-031. Then decide whether ADR-032 is a product you want, before letting it reshape 029 and 030 any further.**

### Update — 2026-07-14: a node-by-node audit of the feature map found three features that exist only on paper

Verifying the companion diagram against source (grep, not ADRs) surfaced a class of drift this review had not looked for: **features that are documented, diagrammed, and in one case *promised to users in-app*, but do not exist in code.**

❌ **The in-app help tells users about a feature that was never built — and it is live in production.** `mobile/src/help-content/topics.ts:319,335` promises curated **starter libraries**. On disk, ADR-028 D5's starter list is **spec-only**: `mobile/src/openshelves/types.ts:35` declares `isStarter`, and the sole writer (`feedStore.ts:36`) hard-codes `isStarter: false`. There is **no Gutenberg/IA/Feedbooks URL constant anywhere in source** — the only such strings are test fixtures. So the Help System — *the very subsystem §4 praised for its CI coverage gate* — is currently shipping **a false claim to users**. The gate enforces that every feature has a help topic; **nothing enforces that every help topic has a feature.** That is the exact inverse failure, and it is worse, because it is user-visible. Fix the copy today; ship the starter list or delete the promise.

❌ **"Lesson / quiz generation" is half-fiction.** `backend/src/generate/tasks.py:268` rejects anything that is not a lesson (`format '{format}' not yet supported in this MVP`); `LessonOutput` has no quiz field; `pipeline/prompts.py:315 build_quiz_prompt` is **dead code with zero callers**; and the mobile client permanently pins `format: "lesson"`. Quizzes only ever *render* — they arrive inside **imported** OnDemand books. Mentible has never generated one.

❌ **"Versioned BookTemplates" (ADR-007, Accepted 2026-06-03) does not exist.** Zero hits for `BookTemplate` / `template_version` / `template_id` across `backend/src`, `compiler/src`, `mobile/src`, `pipeline`. The only "templates" are a generation-params struct and a static markdown outline. **An ADR marked Accepted, cited in this review's own §1 as a delivered strength, with no implementation.** That inverts the pattern flagged above: there the code ran ahead of the decision; here the decision ran ahead — and then nothing followed.

⚠️ **Two more labels overstate what shipped.** "Cover motifs" is **one hard-coded editorial cover** (`compiler/src/cover.ts:6-23`), not a motif system. "Glossary / front-matter" **renders** but has **no authoring surface** — nothing in the app writes `book.metadata.glossary`, so every Mentible-authored book will forever fail the trust manifest's own `_has_glossary` check (`backend/src/export/trust.py:97`).

**The pattern worth naming.** This project's documentation discipline is genuinely strong — 32 ADRs, a CI-enforced help gate, honest status docs. But that discipline has been aimed almost entirely at **recording intent**, and there is no mechanism anywhere that checks **whether the intent was carried out**. ADR-007 says templates; there are none. The help says starter libraries; there are none. The diagram said quizzes; there are none. Each artifact is internally consistent and collectively they describe a product that is somewhat richer than the one that exists. **The next gate this repo needs is not another doc — it is an assertion that the docs are true.**

⚠️ **ADR-028's own launch prerequisites are still open, and ADR-032 now depends on them.** ADR-028 **D5** (the curated starter list) is **spec-only** (`docs/superpowers/specs/2026-07-14-open-shelves-starter-list-design.md`; the only `gutenberg` strings in source are **test fixtures**), **D8**'s `external-feed` library discriminator has **zero hits** in source, and **OQ2** declares live-verification of the starter feeds a **"launch prerequisite"** that has not been done — flagging that Internet Archive's controlled-digital-lending items "require an account and would collide with D4's no-auth guardrail." **ADR-032 D12/D14's entire anti-poisoning design rests on that curated source allowlist** — the one artifact ADR-028 never shipped. The newest ADR's principal safety control is grounded in the oldest ADR's unfinished prerequisite.

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

⚠️ **The seam is tested in its own repo, not here.** Mentible's CI installs `wegofwd-llm` from the git pin but runs none of the seam's 48 tests; a seam regression at a new tag is only caught if Mentible re-pins and its own tests happen to exercise the changed path.

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

⚠️ **No `CONTRIBUTING.md` / multi-repo dev runbook** — and the multi-repo story is now more complex (Mentible + `wegofwd-llm` + Pramana, editable-install dance noted only in a `requirements.txt` comment).

### Update — 2026-07-06: in-app help is now data-authored *and CI-enforced* (Help System, `main@c67b2da`)

- ✅ **Documentation-freshness is, for the first time, a build-time gate — and it directly attacks this section's own headline gap.** The Help System (proposal `docs/proposals/2026-07-05-help-system.md`; PRs #275/#277/#278/#279/#280/#281) makes help *data*: a `FEATURES` registry, a `featureKey` on each `HelpTopic`, and a **hard-fail jest coverage gate** (`mobile/__tests__/help/coverage.test.ts`, run in Mobile CI) that turns the build **red if any declared user-facing feature has no Help topic**. Backed by a **Definition-of-Done in `CLAUDE.md`** ("shipping a feature isn't done until its Help is updated") and a PR-template checkbox. Contextual `?` chips deep-link controls to their topic. This is the enforced-not-remembered version of documentation the rest of §4 keeps asking for — a feature literally cannot ship without its in-app help.
- **It's authored once, rendered everywhere.** Topics are structured blocks (text/steps/link/defs/action) rendered to the Help tab, hints, and chips from one source — no per-surface copy-paste drift.

⚠️ **The gate is scoped to in-app *help topics*, not the top-level status docs.** It enforces feature→topic coverage; it does **not** touch the doc-drift flagged above — `CLAUDE.md`'s stale "Pre-MVP / directory stubs only" header and the ~140-commit-stale `docs/STATUS.md`. The best doc-freshness mechanism in the repo guards the newest doc surface while the oldest, most-read headers stay wrong. Point the same enforcing instinct at the status headers.

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

### Update — 2026-07-14: ADR-032 amends ADR-001 — **this section's foundation is the thing being changed**

Everything above rests on ADR-001: *the vendor never holds a key.* **ADR-032 amends ADR-001** so the hosted tier's RAG runs on **managed keys**. The BYOK guarantees are not being broken — the managed path keeps keys server-side and never exposes them (ADR-031 D7), and free-tier Gemini is deliberately never comped "because it trains on data." But the *shape of the threat model changes*, and three findings follow:

❌ **The per-account spend ceiling — cited by ADR-031 D3/D8, ADR-032 D10, and ADR-032 D15 as the control that bounds abuse — ships disabled.** `backend/config.py`: `managed_account_spend_ceiling_micros: int = Field(default=0)` (`0` ⇒ no ceiling). It is currently harmless only because `managed_plan_emails` defaults to `""` (nobody eligible). **The day the allowlist becomes non-empty, three ADRs' abuse arguments become vacuous simultaneously.** Set a real ceiling and make the service **refuse to enable managed access while the ceiling is 0** — the same fail-closed instinct already applied to the shelves rate limiter and the all-zeros master key.

⚠️ **ADR-032 D15 creates the portfolio's first *unauthenticated-cost* surface.** Free-tier PD grounding is explicitly **not** gated on managed billing, and D14's demand-driven ingestion lets a **free** user trigger the server to fetch and embed a **whole book** on the vendor's managed key. The named mitigations ("per-account rate limits + a query ceiling") carry **no numbers in the ADR**. Sybil-farming a free tier that spends the vendor's tokens is a materially different security problem from anything Mentible has faced — and ADR-031 D8 already warns that comp grants "invite multi-account (Sybil) farming," with today's mitigation being only that grants are *owner-discretionary, not self-serve*. **D15 makes a token-spending capability self-serve.**

⚠️ **Corpus poisoning is correctly identified and correctly designed against — but the defence depends on an unshipped artifact.** ADR-032 **D14** (never accept book bytes from a client; the server fetches from the vetted source) and **D12** (trust the source, not the file's `Rights:` claim — *"a pirated EPUB can simply assert `Rights: Public domain`"*) are the right controls for a corpus that **serves every user**, where a single injected document could "steer other users' generations." The gap is that both rest on **ADR-028 D5's curated source allowlist, which is spec-only** — no allowlist exists in code, and ADR-028's own OQ2 still lists live feed verification as an unmet launch prerequisite.

✅ **Credit where due: the Open Shelves security work is the strongest in the repo.** SSRF resolve-then-check with literal-IP short-circuit and CGNAT blocking, a fail-closed per-IP limiter, manual-redirect re-validation, a content-type allowlist, and `Authorization`/`Cookie` stripping on every hop — all shipped **with** the feature, on an endpoint that is anonymous by design. That is the discipline §5 has praised since v1.0, applied to a genuinely new attack surface.

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

### Added 2026-07-14 — the ADR-028 → ADR-032 expansion

| Priority | Action | Area |
|---|---|---|
| **P0** | **Lock CORS off `*` on the live backend.** `backend/main.py:80` still reads `allow_origins=["*"]` — but the "before any public URL" precondition v2.0 attached to this finding **has been crossed**: prod is live at `mambakkam.net/mentible-api` and its request bodies carry the user's BYOK key. Auth (Supabase JWKS) and a per-IP limiter now exist and blunt it; the wildcard does not belong in a shipped config. **Highest-severity open item in this document** | Security |
| **P0** | **Set a real `managed_account_spend_ceiling_micros` and refuse to enable managed access while it is `0`.** It ships `default=0` (no ceiling) while **three ADRs** (031 D3/D8, 032 D10, 032 D15) cite it as *the* control that bounds abuse and cost. Harmless only because `managed_plan_emails=""`; the day that allowlist is non-empty, all three arguments go vacuous at once | Security / Cost |
| **P0** | **Fix the in-app help that promises starter libraries which do not exist** (`mobile/src/help-content/topics.ts:319,335`). ADR-028 D5's starter list is spec-only (`isStarter` is hard-coded `false`), so this is a **user-visible false claim live in production today**. Either ship the list or change the copy — and add the inverse of the coverage gate: **every help topic must map to a feature that exists**, not just every feature to a topic | Documentation / Trust |
| **P0** | **Put numbers on ADR-032 D15 before any of it is built** — the free-tier rate limit, the query ceiling, and a cap on free-user-triggered **ingestion** (D14 lets a free user make the server embed a whole book on managed keys). D15 concedes it "breaks D10's abuse argument" and then names no figures | Security / Cost |
| P1 | **Answer ADR-032 OQ-A1: do Mentible-*authored* books go to the server?** D11 removed uploads but is silent on manuscripts. If yes, server-side RAG runs over the user's unpublished work, which D6 concedes "cannot be zero-knowledge" — the deepest cut into ADR-014 in the set, currently an open owner decision inside an ADR that claims to resolve the open decisions | Architecture / Privacy |
| P1 | **Re-justify the paid hosted tier, or drop it.** ADR-032's own **OQ-A4** asks whether it still earns its price and its D7 legal burden now that uploads are device-local (D11) and the PD corpus is free (D15). A tier amended away twice, whose abuse argument its author calls broken, should be re-decided before it is built — and 029/030's hosted halves hang off it | Architecture / Product |
| P1 | **Reconcile ADR-032 and ADR-029 with themselves.** The D11–D15 amendment was appended without updating the tail: ADR-032's Scope still says "PD + user-own-uploads only" and "not shippable before managed billing" (both falsified); `SBQ-HOST-002` still says user-upload ingestion; `SBQ-HOST-005` still gates on a ToS clause D11 called "no longer needed"; Consequences still claims a GDPR footprint over "readable user content." **ADR-029's untouched Scope block still promises "no server-side index, corpus, or query log"** while its header says hosted. The ADRs are this project's best artifact — don't let them acquire the doc-drift of §4 | Documentation / Architecture |
| P1 | **Ship ADR-028 D5's curated source allowlist** (spec-only today; the only `gutenberg` strings in source are test fixtures) and close **OQ2**'s live-feed verification, still declared a *launch prerequisite*. **ADR-032 D12/D14's entire anti-poisoning design rests on this allowlist** — the newest ADR's principal safety control is grounded in the oldest ADR's unfinished prerequisite | Architecture / Security |
| P2 | **Mark ADR-028 Accepted.** ~30 source + ~20 test files are merged under a decision still marked *Proposed*. With a shipped feature and three code-free ADRs all sharing the same status, *Proposed* now carries **zero information** about intent to build | Documentation |
| P2 | **Build `Plan.features` or stop citing it.** ADR-031 D4 (feature entitlements) is the ADR's one net-new axis and it does not exist — `billing/plans.py:20-25` has no `features` field, so **EPUB/PDF export, the first thing D4 exists to gate, is ungated** | Architecture |
| P2 | Refresh [`mentible_enhanced_features_mindmap.drawio`](mentible_enhanced_features_mindmap.drawio) — it marks Open Shelves "planned" (it is built), calls ADR-029/030 "candidates" (both are real *Proposed* ADRs), and predates ADR-031/032 entirely. A status diagram that lags the repo by four days is the §4 doc-drift finding in a new surface | Documentation |
| P1 | **Reconcile ADR-007 (Accepted) with reality: versioned BookTemplates do not exist** (zero hits in code). Either build them or move the ADR to Superseded — an *Accepted* ADR with no implementation is worse than a *Proposed* one, because readers trust it | Architecture / Documentation |
| P2 | **Split the "lesson / quiz generation" claim.** `generate/tasks.py:268` rejects every non-lesson format and `build_quiz_prompt` is dead code — Mentible has never generated a quiz. Either delete the dead prompt path or build the format; meanwhile stop describing quiz generation as a capability | Code Quality / Documentation |
| P2 | **Delete `fly.toml` and `docs/DEPLOY_FLY.md`.** Untouched since 2026-05-27, still named `studybuddyq-backend`, superseded by the Hetzner VPS deploy (`docs/STATUS.md:254` says so outright). Dead deploy config is a trap for the next contributor | Ops |
| P2 | Give **glossary** an authoring surface, or stop scoring books on it — nothing writes `book.metadata.glossary`, so every Mentible-authored book permanently fails `trust.py:97 _has_glossary` | Code Quality |
| P3 | Rename "cover motifs" → "editorial cover (single design)" — `compiler/src/cover.ts` is one hard-coded layout, not a motif system | Documentation |
| P3 | Build ADR-028 **D8**'s `external-feed` library discriminator (zero hits in source) — without it, feed-sourced and authored books are indistinguishable in the library, which ADR-032's global book identity (**OQ-A2**, "needs a concrete scheme before build") will need | Architecture |

### Standing (from v2.0, 2026-06-09 — statuses re-verified 2026-07-14)

| Priority | Action | Area |
|---|---|---|
| ~~P1~~ | ✅ **CLOSED** — ~~Reconcile the `wegofwd-llm` version pin~~ → now `@v0.2.0` (`requirements.txt:35`). **The registry half stands, and has doubled:** `wegofwd-secure @ v0.1.0` is a *second* git-pinned, registry-less dependency (`requirements.txt:42`) | Architecture / Supply chain |
| ~~P1~~ | ✅ **CLOSED / OBSOLETE** — ~~Deploy backend to Fly~~ → **shipped on Hetzner**, prod live + BYOK generation working. `fly.toml` is now vestigial; delete it or mark it dead so it stops misleading on the deploy target | Verification |
| P1 | Replace in-process `BackgroundTask` with Celery/Redis, or explicitly document the restart-data-loss window as accepted for MVP — **now materially worse: this runs in production, so an unlucky deploy drops a live user's in-flight job** | Architecture |
| ~~P1~~ | ✅ **CLOSED** — ~~Fix the stale headers in `CLAUDE.md` / refresh `docs/STATUS.md`~~ → both done; `STATUS.md` current to 2026-07-03 | Documentation |
| **P0** | ⬆️ **ESCALATED — see the new P0 above.** ~~Lock CORS off `*`… **before any public URL**~~ → the public URL now exists and `main.py:80` is unchanged. Rate-limiting now partially exists (`core/rate_limit.py`); the all-zeros master-key guard was not found in `config.py` | Security |
| P2 | Decide ADR-010 (narrative mode) and ADR-011 (Pramana handoff) from *Proposed* — both have prototype code ahead of the decision | Architecture |
| P2 | Pin + version the `book.json` schema and validate it on both boundaries | Architecture |
| P2 | Add on-device (Detox/Maestro) E2E for the multi-provider BYOK loop, and a committed live-provider smoke test gated on an opt-in secret | Testing |
| P2 | De-duplicate the `16384` `max_tokens` defaults now that clamping lives in the seam | Code Quality |
| P2 | Point the doc-freshness *enforcing instinct* at the status headers — the Help coverage gate (2026-07-06) hard-fails CI on an undocumented feature, yet the oldest, most-read docs (`CLAUDE.md` "Pre-MVP" header, stale `docs/STATUS.md`) drift unchecked; add a lightweight staleness/assertion guard so the newest doc surface isn't the only enforced one | Documentation |
| P3 | `git rm` the stale `tests/llm/__pycache__/*.pyc` orphans (the modules moved to `wegofwd-llm`) | Code Quality |
| P3 | Add a `CONTRIBUTING.md` / multi-repo dev runbook (Mentible + `wegofwd-llm` + Pramana, editable installs) | Documentation |
| P3 | Note in ADR-001's threat model that the in-process `del api_key` shred is best-effort | Security |

---

*The **2026-07-14 addendum** (§1 and §5 updates, the added Priority Actions block) is measured against `main@28a62c8` — 677 commits, 135 of them since 2026-07-06 — reading ADR-028 through ADR-032 in full plus the companion brief `docs/proposals/2026-07-12-server-hosted-library-and-rag.md`, and verifying implementation status by grep across `backend/src`, `mobile/src`, `pipeline/`, and `compiler/`. All five new ADRs are **Proposed**; ADR-028 is nonetheless merged and shipping. Claims that a capability is "paper" are word-boundary-grep negatives (`rag`, `embedding`, `vector_store`, `fts5`, `watch_manifest`, `currency_agent`, `Plan.features`), not inferences from the ADR text. The `managed_account_spend_ceiling_micros: int = Field(default=0)` finding is read directly from `backend/config.py`. Tests were not executed in the review environment.*

*This critique is a point-in-time review measured against the code on disk at `40166ee` (branch `main`, 2026-06-09), the 13 ADRs, the commit log `e1c66f7..HEAD` (97 commits), and the sibling repos `wegofwd-llm` (latest tag `v0.1.1`) and `pramana` (HEAD `e2958ef`, branch `feat/ai-drafted-approved-content`). Deployment status and on-device UX are **self-reported in `docs/STATUS.md`** (now stale) and were not verifiable from source; pytest could not be executed in the review environment (no `pytest` module installed), so the 422-scrub claim is verified by reading the handler, the `scrub_validation_errors` implementation, and the asserting test, not by a green run. The brand "Mentible" is adopted per ADR-006 pending trademark/domain clearance; the repo and some identifiers remain `Mentible` / `studybuddy-q` intentionally. Supersedes v1.0 (2026-06-02 @ `e1c66f7`).*
