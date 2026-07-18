# wegofwd-video — Code Review & Critique

**Reviewed:** 2026-07-01 (v1.0 — first review; admission of the 2nd portfolio-level shared dependency to the critique suite)
**Repo:** `wegofwd2020-hub/wegofwd-video` · reviewed in place at `/home/sivam/Documents/AIStuff/wegofwd2020-hub/wegofwd-video`
**HEAD:** `233f248` (2026-06-30) — 4 commits, all on 2026-06-30 (scaffold → v0.1.1 py3.10 floor → v0.1.2 Veo live-call wiring → v1.0.0 freeze)
**Phase:** v1.0.0 frozen contract; **load-bearing for two products** on two provider paths
**Reviewer:** Claude (Anthropic)
**Rating key:** 🟢 Strong · 🟡 Gap / Risk · 🔴 Critical Issue

---

## Why this project gets top-level watch

`wegofwd-video` is the shared **multi-provider video-generation seam** for the WeGoFwd2020 product family — the exact same architectural move as `wegofwd-llm`, one domain over. Per ADR-026 (amended 2026-06-30) it is now consumed by:

- **pramana** — the AI `veo` path (BYOK Veo + S3), drafting a compliance video at DRAFT time and materialising it onto the immutable `CourseVersion` at publish (`pramana#4`).
- **kathai-chithiram** — the `deterministic-renderer` path, wrapping its own in-process `SceneScriptRenderer` so child content never leaves its trust boundary (`kathai-chithiram#12`).

Both pin `git+…@v0.1.2`. That makes `wegofwd-video` the **second cross-cutting shared dependency in the portfolio** after `wegofwd-llm`, and the same asymmetry applies: a regression here is not a one-product bug, it is a portfolio incident touching both the SOX-compliance content lineage (pramana) and the child-safeguarding render path (kathai). 741 production LOC front the entire video lineage of two apps. That blast-radius-vs-size ratio is the watch case (§9).

---

## Executive Summary

This is a disciplined, deliberately small library that copies the best of `wegofwd-llm` verbatim and specialises it for video: a frozen-dataclass typed contract (`VideoCapabilities` / `Ingredient` / `Shot` / `VideoBrief` / `VideoRequest` / `VideoResult`, `contract.py`), a `VideoProvider` ABC, a single-source registry (`VIDEO_PROVIDER_REGISTRY` + `ROLE_DEFAULTS`, `registry.py`), a BYOK `build_provider()` that enforces the allow-list *before* construction and imports the SDK lazily, an `assert_brief_within_capabilities()` pre-dispatch conformance gate, and a `provenance()` stamp carrying `engine/provider/model/model_verified/integration_version/contract_version/seed`. The core has **zero runtime dependencies** (`pyproject.toml:22`); the Google SDK is an optional `[veo]` extra, lazily imported (`veo.py:180-187`). Key discipline is real and, notably, **better tested than `wegofwd-llm` was at the same age**: two regression tests directly guard key leakage — `test_no_key_in_repr` (`test_providers.py:207-209`) and `test_veo_generate_maps_auth_error_keyfree` (`test_providers.py:171-193`, which raises an SDK error literally containing `super-secret` and asserts it is absent from the mapped `VideoError`). `wegofwd-llm`'s critique named the *absence* of exactly this test as its §5 #1 ask; `wegofwd-video` shipped it on day one.

The design rigor extends to process: ADR-026 D7 is a **conscious, documented exception** to ADR-019's "extract on the second real consumer" rule, risk-capped by staying at v0.x and gating v1.0 on "both real integrations green." That gate is recorded as MET (both consumer PRs merged), and the extract even paid the anticipated tax — kathai being Python 3.10 forced the `requires-python` floor down to `>=3.10` in v0.1.1 (`pyproject.toml:10-14`), exactly the "late discovery" D7 named as the cost of building ahead of the rule. This is unusually honest engineering.

The risks are the risks of being one week old and frozen anyway. **The `veo` provider has never made a live call** — the whole submit→poll→download flow (`veo.py:119-158`) is wired and unit-tested against a fake SDK client, but no real generation has succeeded. Despite that, the registry stamps **`model_verified=True` for `veo`** (`registry.py:63`), which the *same file's* header comment contradicts ("NOT yet live-tested … flip `model_verified` after the first real generation", `registry.py:8-12`) and which the README's own provider table calls "docs-verified; awaiting first real run." A provenance record that rides onto an immutable `CourseVersion` therefore asserts a live-verified basis that does not yet exist (§6 🔴). **`runway` and `kling` are worse than unverified placeholders — they are dead on arrival:** they appear in `available_providers()`, resolve through `validate_selection()`, and produce a `provenance()` stamp, but `build_provider()` has no constructor branch for them and always raises `VideoConfigurationError("no constructor wired…")` (`registry.py:231`). A picker endpoint that lists `available_providers()` will offer two providers that can never be built. **Veo's headline feature, Ingredients-to-Video, is deliberately not wired** — `generate()` raises if a brief carries any ingredient (`veo.py:123-127`), and a test *asserts* it stays that way (`test_providers.py:164-168`). **There is no CI in the repo** (no `.github/workflows/`) and no `.watch/` — the test suite that the README calls "the conformance gate [that] travels with the code" is run by nobody automatically. Distribution is `git+https` and both consumers pin `v0.1.2` while the package is already `v1.0.0`, so neither consumer is actually on the frozen contract they gated. And `license = "Proprietary"` (`pyproject.toml:16`) sits on a package the README frames as a shared family member installed cross-repo — the same license/distribution tension flagged in `wegofwd-llm-critique.md`.

Zero `TODO`/`FIXME` in source. 30 `def test_` across 5 files, 362 test LOC, none hitting live APIs (correct). Nothing here is a shipped-and-broken bug in the exercised paths; everything flagged is a "frozen at v1.0 before it was finished" tension, and the package is candid about most of it.

---

## Snapshot

| Metric | Value |
|---|---|
| Commits on `main` | 4 (all 2026-06-30) |
| HEAD | `233f248` (2026-06-30) |
| Released versions | v0.1.0 → v0.1.1 (`>=3.10` floor) → v0.1.2 (Veo live-call wiring) → v1.0.0 (freeze) |
| Python source LOC | 741 (contract 126 · registry 231 · errors 45 · providers: veo 207 + local_render 48 · `__init__` 82) |
| Test LOC | 362 across 5 files |
| Test functions (`def test_`) | 30 (providers 10 · registry 7 · allowlist 6 · capabilities 4 · versioning 3) |
| Providers in registry | 4 (`veo`, `deterministic-renderer`, `runway`, `kling`) |
| Providers with `model_verified=True` | 2 (`veo`, `deterministic-renderer`) |
| Providers actually constructable by `build_provider()` | 2 (`veo`, `deterministic-renderer`) |
| Providers dead-on-arrival in `build_provider()` | 2 (`runway`, `kling` — no constructor branch) |
| Providers with a **live**-verified model | 0 (`veo` is docs-verified only; `deterministic-renderer` is caller-supplied) |
| `VIDEO_CONTRACT_VERSION` | 1 |
| TODO / FIXME / XXX in source | 0 |
| CI present | 🔴 none (`.github/workflows/` absent) |
| In-repo watch config | 🔴 none (`.watch/` absent) |
| Runtime dependencies | 0 (core); optional `[veo] = google-genai>=0.3` (lazy) |
| Distribution | `git+https` (no PyPI); consumers pin `v0.1.2` (package at `v1.0.0`) |
| License | `Proprietary` (`pyproject.toml:16`) |
| Python required | `>=3.10` |
| Current production consumers | pramana (`veo`) · kathai-chithiram (`deterministic-renderer`) |

---

## Per-area ratings

| # | Area | Rating | One-line |
|---|---|---|---|
| 1 | Architecture | 🟢 | Clean seam; capability pre-check + provenance + role-pinning, all single-sourced. |
| 2 | Code quality | 🟢 | Frozen dataclasses, `repr=False` on binaries, `raise … from None` everywhere, 0 TODO. |
| 3 | Test coverage | 🟡 | 30 focused unit tests incl. two real key-leak guards; but no live smoke and **nothing runs them** (no CI). |
| 4 | Documentation | 🟢 | README is accurate and ships a provider status matrix at launch — ahead of where `wegofwd-llm` started. |
| 5 | Security / key discipline | 🟢 | The standout: BYOK enforced pre-call, code-based (not string-based) error mapping, two leak regression tests. |
| 6 | Provider readiness / verification | 🔴 | `veo` `model_verified=True` but never live-run; `runway`/`kling` DOA in `build_provider()`; Ingredients deferred. |
| 7 | Distribution / CI / release | 🔴 | No in-repo CI or watch; consumers pinned `v0.1.2` while frozen at `v1.0.0`; `Proprietary` on a cross-repo shared lib. |
| 8 | Scalability / Ops | 🟢 | Pure, stateless, zero-dep core; caller owns queue + storage — correct boundary for a minutes-long, MB-scale call. |

---

## 1. Architecture 🟢

### Strengths

- 🟢 **The contract is the seam, and it is genuinely provider-agnostic.** `contract.py` defines the full brief lineage (`VideoBrief` → `Shot`/`Ingredient`) plus `VideoRequest`/`VideoResult` and the `VideoProvider` ABC as frozen dataclasses. Adding a provider is implementing one ABC (`model` property + `generate()`) and adding a `VideoProviderSpec` row. Consumers never branch on vendor.
- 🟢 **Model ids live in exactly one place.** `ROLE_DEFAULTS` (`registry.py:109-113`) maps logical roles (`narrative-video`→veo, `safety-render`→deterministic-renderer, `fast-preview`→veo) to `(provider, model)` pairs; `resolve_role()` is the only call sites need. No app hardcodes `"veo-3.1"`.
- 🟢 **Capability pre-check is a real pre-dispatch gate.** `assert_brief_within_capabilities()` (`registry.py:167-185`) validates resolution, aspect, duration, and *ingredient count* against the spec's `VideoCapabilities` and raises `VideoCapabilityError` listing **every** violation before a single vendor byte is sent (`test_capabilities.py` exercises the pass, the overlong-clip, the unsupported-resolution, and the "renderer takes no ingredients" cases). This is the right shape for an expensive, minutes-long call — fail in microseconds, not after a 90-second poll.
- 🟢 **Provenance is first-class and reproducibility is threaded end-to-end.** `provenance()` (`registry.py:149-164`) returns the stampable record ADR-026 D6 specifies, and `seed` flows `VideoRequest.seed` → `build_request` config (`veo.py:111-112`) → `VideoResult.seed` (`veo.py:157`) → `provenance(seed=…)`. The `deterministic=True` capability flag on the renderer (`registry.py:78`) is the honest counterpart: same seed/brief reproduces frames exactly. A stale render is detectable and regenerable.
- 🟢 **The `deterministic-renderer` is the architecturally load-bearing idea.** `CallableRenderProvider` (`local_render.py:25-48`) adapts a *caller-supplied* `render_fn(VideoRequest) -> VideoResult` to the ABC. This is what lets kathai adopt the shared registry/brief/provenance vocabulary **without any AI vendor and without child content leaving its process** — the whole reason ADR-026 rejects a shared service. A non-AI provider under the same abstraction is a genuinely good design move.
- 🟢 **Allow-list is enforced before construction.** `build_provider(..., allowed=…)` calls `validate_selection` first (`registry.py:204`), so an excluded provider raises `VideoNotAllowedError` before any provider object — or vendor call — exists (`test_allowlist.py:31-33`).

### Gaps & Risks

- 🟡 **Two sources of truth for the brief shape.** The runtime contract is the `contract.py` dataclasses, but `schema/video_brief.v1.json` also ships. Nothing enforces that the JSON Schema and the dataclasses agree; they can drift silently. Either generate one from the other, or add a test that validates a `VideoBrief` round-trip against the schema.
- 🟡 **Duplicated capability definition in `VeoProvider`.** `VeoProvider.__init__` carries a hardcoded fallback `VideoCapabilities(max_duration_s=60, resolutions=("1080p",), …)` (`veo.py:88-90`) that differs from the registry spec (`registry.py:54-61`: adds `720p`/`4k`, aspect ratios, `upscaling`). `build_provider` always passes the spec caps, so the fallback only bites a direct `VeoProvider(...)` construction — but it is a drift trap. Have the provider require caps, or read them from the registry.
- 🟡 **No submit/poll job protocol is exposed, only a blocking `generate()`.** ADR-026 D2 describes "a synchronous `generate()` **plus** a submit→poll job protocol; the caller wires that to its own queue." Only the former exists — the poll loop is private inside `VeoProvider._await_operation` (`veo.py:160-169`). A caller that wants to persist a vendor operation id and poll across worker restarts (the natural Celery shape) has no seam to do so and must hold a worker for up to 600s. Sketching a `submit()`/`poll()` pair is the honest v1.1 ask.

---

## 2. Code Quality 🟢

### Strengths

- 🟢 **Frozen dataclasses with binary fields excluded from `repr`.** `VideoResult.asset_bytes` and `.raw` are both `field(default=None, repr=False)` (`contract.py:97,105`) — MB-scale bytes and vendor payloads never bloat or leak into an incident log line. All contract types and `VideoProviderSpec` are `frozen=True`.
- 🟢 **`raise … from None` on the one exception path that matters.** The Veo generate loop catches `VideoError` and re-raises it, then catches everything else and does `raise self._map_error(exc) from None` (`veo.py:142-145`) — breaking the chain so a raw SDK exception's `repr()` can never surface. `resolve_role` does the same (`registry.py:143-146`).
- 🟢 **PEP 561 typed.** `wegofwd_video/py.typed` ships in the wheel (`pyproject.toml:31-32` packages `wegofwd_video`), so consumers get type-checking against the public surface.
- 🟢 **Ruff config mirrors the family verbatim.** `select = ["E","W","F","I","B","C4","UP","S","T20","RUF"]` (`pyproject.toml:40`) — identical shape to `wegofwd-llm`, so a file lints identically here and in any consumer. The `S` (flake8-bandit) selection on non-test code is the right paranoia for a key-handling library.
- 🟢 **`render_brief_text` is pure and deterministic** (`veo.py:40-65`) — brief flattening is unit-testable with no SDK, and `test_render_brief_text_includes_global_block_and_shots` pins the exact output format including the global block and per-shot pipe layout.
- 🟢 **Zero `TODO`/`FIXME`/`XXX` in source.** Verified.

### Gaps & Risks

- 🟡 **`render_brief_text` renders ingredient lines that `generate()` refuses to send.** The flattener emits `INGREDIENT[…]` lines (`veo.py:49-50`) and a test asserts they appear, yet `generate()` hard-rejects any brief with ingredients (`veo.py:123-127`). The prompt-shaping is ahead of the dispatch path — harmless today, but a reader could reasonably assume ingredients work end-to-end because the prompt text contains them.
- 🟡 **`_map_error` reads three possible code attributes but the SDK's real one is unconfirmed.** `getattr(exc, "code"/"status_code"/"response_status")` (`veo.py:196-200`) is a reasonable net, but with zero live calls it is unverified which (if any) `google-genai` actually exposes. If the live SDK carries the status somewhere else (e.g. nested in a `response` object), every real error collapses to the generic `VideoResponseError("Veo request failed")` and the typed `VideoAuthError`/`VideoRateLimitError` routing silently never fires. This is the kind of thing only a live smoke test catches.

---

## 3. Test Coverage 🟡

### Strengths

- 🟢 **30 tests over 5 files, no live APIs.** `test_providers.py` (10) mocks the entire Veo SDK surface with a fake client (`_FakeClient`/`_FakeOps`/`_FakeFiles`, `test_providers.py:101-145`) and exercises submit→poll→download with a forced two-iteration poll (`done_after=2`). `test_registry.py` (7), `test_allowlist.py` (6), `test_capabilities.py` (4), and `test_versioning.py` (3) cover the registry, allow-list ordering, capability gate, and provenance shape.
- 🟢 **Two real key-leak regression tests — the thing `wegofwd-llm` lacked.** `test_no_key_in_repr` (`test_providers.py:207-209`) asserts a constructed provider's `repr()` omits the key; `test_veo_generate_maps_auth_error_keyfree` (`test_providers.py:171-193`) makes the fake SDK raise an error *containing* `super-secret` and asserts it is absent from the raised `VideoAuthError`. `wegofwd-llm-critique.md` §5 #1 asked for precisely this; here it exists on day one. This is the single best thing about the test suite.
- 🟢 **The honesty convention is tested.** `test_placeholders_are_marked_unverified` (`test_registry.py:49-52`) and `test_provenance_surfaces_unverified_honestly` (`test_versioning.py:19-24`) lock `runway`/`kling` to `model_verified=False` so a stamp can never over-claim them.
- 🟢 **The deferred-Ingredients decision is pinned by a test.** `test_veo_generate_rejects_ingredients_until_wired` (`test_providers.py:164-168`) asserts the guard fires — the deferral is deliberate and regression-guarded, not an oversight.

### Gaps & Risks

- 🔴 **Nothing runs these tests automatically.** There is no `.github/workflows/`. The README calls the suite "the conformance gate [that] travels with the code," but for a dependency two products build on, a gate nobody runs on push is a blind spot. A trivial `ci.yml` (`pip install -e ".[dev,veo]"` → `pytest` → `ruff check`) is a 30-minute fix and closes the largest hole in the package.
- 🟡 **No live smoke test for `veo`, gated on an env key.** Every §1–2 §6 risk that "only a live call catches" (SDK error-code shape, model-id validity, the download-bytes lazy path, base-URL correctness) is currently caught by nobody. A single gated `generate` of a 4-second clip when `VEO_API_KEY` is present would surface model deprecation before pramana does.
- 🟡 **No test asserts `build_provider` refuses `runway`/`kling`.** The DOA behaviour (§6) is untested; a future contributor could wire a half-constructor and no test would notice the mismatch between "listed as available" and "constructable."
- 🟡 **No coverage gate.** For a library, per-module coverage matters; add `--cov-fail-under=…` once CI exists.

---

## 4. Documentation 🟢

### Strengths

- 🟢 **The README ships a provider status matrix at launch** (`README.md:31-36`) — a table with `status` and `notes` columns that names `veo` as "live call wired (docs-verified; awaiting first real run)" and `runway`/`kling` as "UNVERIFIED / placeholder." `wegofwd-llm`'s critique asked for exactly this table as a §7 item; `wegofwd-video` has it out of the box. This is the right place to surface the 2-of-4 readiness state.
- 🟢 **Module docstrings carry the *why*.** Every file opens with the design choice — `local_render.py`: "Child content never leaves the caller's process — there is no key and no vendor"; `veo.py`: the STATUS block explaining the live-call/`model_verified` deferral; `registry.py`: the UNVERIFIED-placeholder policy. These are the comments worth writing.
- 🟢 **ADR-026 is cross-referenced** (`README.md:10`) and the content-contract location (`project-critique/story-video-template/`) is named — a reader can trace back to the full decision and the two worked examples that validated the seam.
- 🟢 **The `pyproject.toml` comments are incident-grade.** The `requires-python` block (`pyproject.toml:10-14`) documents *why* the floor is 3.10 (kathai) and ties it to ADR-026 D7; the `dependencies = []` block explains the zero-dep intent and the lazy `[veo]` extra. This is the comment style other repos should imitate.

### Gaps & Risks

- 🟡 **The `model_verified` truth is split three ways and one of them is wrong.** README says "docs-verified; awaiting first real run"; `registry.py:8-12` says "NOT yet live-tested"; but `registry.py:63` sets `model_verified=True`. A reader who trusts the flag (the machine-readable source) gets the opposite of the prose. See §6 🔴.
- 🟡 **No `CHANGELOG.md`, `CONTRIBUTING.md`, or `SECURITY.md`.** For a frozen-at-v1.0 shared library whose entire promise is "consumers pin and upgrade deliberately," a consumer-facing changelog is table stakes; a `SECURITY.md` documenting the BYOK/no-env/no-chain rules and disclosure path is warranted for a key-handling package.
- 🟡 **The README's own layout comment is stale.** `README.md:77` calls the Veo live call "stubbed (ADR-026 D7)," but the call is wired (`veo.py:119-158`) and the status section (`README.md:84-91`) says so — the layout block just wasn't updated in the same pass.

---

## 5. Security / Key discipline 🟢

### Strengths

- 🟢 **BYOK enforced before any call, in two places.** `build_provider` raises `VideoConfigurationError` if `veo` gets no key (`registry.py:221-222`) and `VeoProvider.__init__` re-checks `if not api_key` (`veo.py:80-81`). The package will not fall back to an env var or vault — it never reads `os.environ` at all.
- 🟢 **Error classification branches on the HTTP *code*, never the exception string.** `_map_error` (`veo.py:189-207`) explicitly avoids stringifying the exception ("the message is generic + the code only, never the exception string, which can echo request details") and returns a typed, key-free `VideoError`. This is the correct, paranoid design.
- 🟢 **The `deterministic-renderer` path has no key and no vendor by construction.** `CallableRenderProvider` holds only a callable and metadata (`local_render.py:28-38`); there is nothing to leak, which is the entire privacy argument for kathai.
- 🟢 **Two leak regression tests** (see §3) — the discipline is guarded by tests, not just review. Materially stronger than `wegofwd-llm` at the same phase.
- 🟢 **Typed hierarchy enables safe boundary mapping.** `VideoConfigurationError`→422, `VideoNotAllowedError`→403, `VideoAuthError`→401, `VideoRateLimitError`→429 (`errors.py`); the API layer routes on type without inspecting messages. `VideoCapabilityError` subclasses `VideoConfigurationError` so a too-big brief maps to 4xx naturally.

### Gaps & Risks

- 🟡 **`key_prefix` is declared but never validated.** `VideoProviderSpec.key_prefix` (`registry.py:42`, e.g. `runway`'s `"key_"`) is documented as a "BYOK shape check" but no code checks it — a wrong-shaped key reaches the vendor and fails there. Cheap client-side validation would fail faster without consuming a (slow, expensive) request.
- 🟡 **No spend / rate-limit budget primitive.** A single expensive call path times out at 600s (`veo.py:77`) with no per-caller cap. For a shared seam where one consumer's runaway loop is a portfolio-wide (and per-clip *costly*) problem, an in-process budget/counter is worth at least sketching — more so than for the text seam because each video call costs real money.
- 🟡 **`raw` is `repr=False` but still carries the full vendor payload** (`contract.py:105`). Correct for logs; but if a caller pickles/serialises a `VideoResult` for a job queue, `raw` (an arbitrary SDK object) goes with it. Document that `raw` is debug-only and must not be persisted.

---

## 6. Provider readiness / verification 🔴

This is the weakest area and the one that most contradicts the "v1.0 frozen" label.

### Findings

- 🔴 **`veo` claims `model_verified=True` while having never made a live call.** `registry.py:63` sets `model_verified=True`; `provenance("veo")` therefore stamps `model_verified: True` (`test_versioning.py:5-16` asserts it) onto records that ride onto immutable `CourseVersion`s in pramana. But the same file (`registry.py:8-12`), the provider docstring (`veo.py:14-17`), the README, and ADR-026's open item all agree the model is **docs-verified, not live-tested**, and that `model_verified` should be **flipped after the first real generation** — which is impossible, because it is already `True`. The flag that exists specifically to encode "known unknown" is, for the one provider that will actually be called, asserting the unknown as known. **Fix:** set `veo` `model_verified=False` until a live run passes (and let the honest flag do its job), or split the concept into `docs_verified` vs `live_verified` so provenance can distinguish "we read the docs" from "we generated a real asset."
- 🔴 **`runway` and `kling` are dead-on-arrival.** Both are in `VIDEO_PROVIDER_REGISTRY`, so `available_providers()` lists them (`test_registry.py:12-18` asserts all four), `validate_selection` resolves them, and `provenance` stamps them — but `build_provider()` has constructor branches only for `deterministic-renderer` and `veo`, then falls through to `raise VideoConfigurationError("no constructor wired for provider …")` (`registry.py:231`). A "GET available video providers" endpoint (which `available_providers()` docstring explicitly says it feeds, `registry.py:118-119`) will therefore offer a picker two options that `build_provider()` can only reject. This is worse than `wegofwd-llm`'s dead `gemma` entry (which at least reached its constructor before failing). **Fix:** filter `available_providers()` to constructable specs, or add an `available: bool` field and honour it, or drop the two rows until a constructor lands.
- 🟡 **Veo's headline capability (Ingredients-to-Video) is unwired and the registry advertises it.** `generate()` rejects any ingredient (`veo.py:123-127`) — a good, loud deferral — yet the spec advertises `reference_images=4` (`registry.py:59`) and `assert_brief_within_capabilities("veo", …, ingredients=2)` *passes* (`test_capabilities.py:7-10`). So the capability gate green-lights a brief that `generate()` will then refuse. The pre-check and the dispatch path disagree about what `veo` can do.
- 🟡 **`deterministic-renderer` is `model_verified=True` but is fundamentally caller-supplied** (`registry.py:80`). Defensible (the *interface* is verified), but it means "verified" has two different meanings across the two `True` rows — one "we checked Google's docs," one "the contract wrapper works." Worth a one-word note.

---

## 7. Distribution / CI / Release 🔴

### Findings

- 🔴 **No CI and no watch in the repo.** No `.github/workflows/`, no `.watch/`. For the 2nd portfolio-level shared dependency, nothing runs the test suite, the linter, or a per-commit re-critique automatically. (§3, §9.)
- 🟡 **Consumers are pinned behind the frozen contract.** Both pramana and kathai pin `git+…@v0.1.2`, but the package is `v1.0.0`. The v1.0 freeze was gated on "both integrations green" — but those integrations are running `v0.1.2`, not the frozen artifact. Either the pins should move to `v1.0.0`, or the "gate met" claim is about `v0.1.2`'s behaviour and v1.0 is untested by any consumer. Worth reconciling explicitly.
- 🟡 **`git+https`, no package registry.** Every un-cached consumer CI run pulls source from GitHub. A private PyPI / CodeArtifact / GitHub Packages closes this — the same ask standing against `wegofwd-llm`.
- 🟡 **`license = "Proprietary"` on a package the README calls a shared family member** installed cross-repo (`pyproject.toml:16`, `README.md:6-8`). Whether the repo is public or private, the Proprietary string plus cross-repo `git+https` distribution wants an explicit consumer-distribution/licensing note — the same tension `wegofwd-llm-critique.md` flagged. Confirm repo visibility and align the license with the intended use.
- 🟢 **Release history is clean and semver-honest** — four commits walking v0.1.0 → v1.0.0 with each version doing one thing, and the `>=3.10` floor drop correctly landed in a v0.1.x minor before the freeze.

---

## 8. Scalability / Ops 🟢

### Strengths

- 🟢 **Zero-dep, stateless, pure core.** No module-level singletons, no warm-up, no global config. A provider is built per call (BYOK); `deterministic-renderer` pulls nothing at all (`pyproject.toml:22`). Correct shape for both a Celery worker (pramana) and an in-process subprocess (kathai).
- 🟢 **The boundary is drawn where ADR-026 D2 says.** The package returns bytes-or-URI and stops; queue (pramana=Celery, kathai=subprocess) and storage (S3/filesystem) are the caller's. For a minutes-long, MB-scale, expensive operation, keeping orchestration and persistence out of the shared lib is exactly right — it is what lets two very different runtimes share one seam.
- 🟢 **Lazy SDK import means the dependency footprint matches the path taken** (`veo.py:180-187`) — kathai's deterministic path never imports `google-genai`.

### Gaps & Risks

- 🟡 **Blocking `generate()` holds a worker for up to 600s** with a 10s poll (`veo.py:77,163-168`). Fine for Celery with a long visibility timeout; a footgun for a naive caller. Pair with the submit/poll seam ask (§1).
- 🟡 **`VideoRateLimitError` is marked "Retryable / failover candidate"** (`errors.py:32`) but no retry/failover/circuit-breaker lives in-package — every consumer writes its own. As with `wegofwd-llm`, a portfolio-wide policy is half the point of a shared seam; sketch the contract even if the implementation stays caller-side.
- 🟡 **No structured logging / metrics hook.** A shared, *expensive* seam is the natural place to centralise per-generation cost/duration/attempt metering. Today every consumer instruments independently. A pluggable observer on `generate()` would let both attach without forking.

---

## 9. Priority Actions

Ranked by risk × leverage.

| # | Action | Why | Effort |
|---|---|---|---|
| 1 | **Fix the `veo` `model_verified` integrity gap** — set it `False` until a live run passes, or split `docs_verified` vs `live_verified`. | The one provider that will actually run stamps `model_verified=True` onto immutable `CourseVersion` provenance despite never having generated. The honesty flag currently lies. | 30 min |
| 2 | **Add in-repo CI** — `pip install -e ".[dev,veo]"` → `pytest` → `ruff check`. | The conformance gate that "travels with the code" is run by nobody. Largest single hole for a 2-product dependency. | 30 min |
| 3 | **Resolve `runway`/`kling` DOA** — filter `available_providers()` to constructable specs, or add `available: bool`, or drop the rows. | A picker fed by `available_providers()` offers two providers `build_provider()` can only reject. | 30 min |
| 4 | **Reconcile the consumer pins** — move pramana/kathai to `v1.0.0`, or state that the frozen contract is `v0.1.2`'s behaviour. | The v1.0 gate was "both integrations green," but both run `v0.1.2`, not `v1.0.0`. | 30 min |
| 5 | **Add a gated live Veo smoke test** (runs only when `VEO_API_KEY` present) and flip `model_verified` on its pass. | Only a live call catches SDK error-code shape, model-id validity, the lazy-download path, base-URL drift. Closes items #1 and half of §2/§6. | Half day |
| 6 | **Align the capability gate with `generate()` for ingredients** — either wire Ingredients-to-Video, or have the pre-check reject ingredients for `veo` until it is. | The pre-check green-lights briefs `generate()` refuses. | 1 h (gate) / 1 day (wiring) |
| 7 | **Resolve `license = "Proprietary"` vs shared cross-repo distribution + confirm repo visibility.** | Same tension as `wegofwd-llm`; friction at minimum, ambiguity at worst. | 1 h (decision) |
| 8 | **Validate `key_prefix` in `build_provider`.** | Declared but unused; cheap client-side shape check fails faster than a slow vendor round-trip. | 1 h |
| 9 | **Sketch a submit/poll job seam + a retry/failover + a metrics-observer contract.** | The errors are typed for retry, the call is minutes-long and costly, and every consumer instruments alone. v1.1 candidates. | Design: 1 day |
| 10 | **Add `CHANGELOG.md` / `SECURITY.md` / `CONTRIBUTING.md`.** | Shared-library hygiene; supports "pin and upgrade deliberately." | 2 h |

---

## 10. Watch case — the 2nd portfolio-level shared dependency

`wegofwd-video` is the **second** member of the `wegofwd-*` family to become load-bearing across multiple products, after `wegofwd-llm`. The watch argument that admitted `wegofwd-llm` applies here with the same force and one extra edge:

- **Blast radius > footprint.** 741 production LOC front the entire video lineage of two products on two different provider paths. A regression is a portfolio incident, not a product bug — and one of the two consumers (kathai) is a child-safeguarding path where a leak of the wrong kind is not a latency blip but a safeguarding failure.
- **You are your own only architectural challenger.** As with `wegofwd-llm`, every consumer of this seam is the same author. ADR-026 D7 is admirably honest that it froze a cross-repo interface ahead of ADR-019's rule; the mitigation was "two green integrations." That gate is claimed met — but at `v0.1.2`, while the frozen artifact is `v1.0.0` and its most important provider has never made a live call. The watch loop is what keeps that gap visible.
- **Shared-scaffolding drift is now a live question.** ADR-026's own open items flag a possible tiny `wegofwd-core` to de-dup `registry`/`provenance`/`errors`, which are near-verbatim copies of `wegofwd-llm`'s. Two copies is the point at which that decision should be scheduled, not deferred indefinitely — the watch is the natural place to track when a third copy (e.g. a future `wegofwd-*`) tips it over.

**Recommended cadence** (mirrors the `wegofwd-llm` proposal, to be confirmed):

- **Weekly:** automated commit-delta check against `main`; any commit ⇒ a sub-agent re-runs §9 against the diff and posts to a dated `wegofwd-video-watch-YYYY-MM-DD.md`. Quiet weeks produce a one-line "no change."
- **On the first live Veo generation:** re-run §6 and confirm `model_verified` was flipped on a live basis, not asserted ahead of it.
- **On every consumer pin bump** (`v0.1.2` → `v1.0.0` and beyond): the watch checks which behaviour changes the consumer is newly exposed to.
- **On a third `wegofwd-*` copy of registry/provenance/errors:** trigger the `wegofwd-core` decision.

---

## 11. Anti-claims

For honesty, this is a **first review based on the source at HEAD `233f248`**. The following are *not* asserted:

- That `wegofwd-video` has ever produced a real video. The `veo` path is wired and unit-tested against a fake SDK client; **no live generation has been verified**, and this review treats the `veo` `model_verified=True` flag as a defect *because* of that.
- That the test suite was executed in this pass. Test files were read and counted (30 `def test_` across 5 files); they were not run here (the review environment could not execute them). Presence/absence of CI was checked by directory listing.
- That `runway`/`kling` behave as their capability flags claim. They are unverified placeholders and, additionally, not constructable — flagged in §6.
- That no key leak can occur. The two regression tests (§5) guard the known surfaces; the claim is "guarded," not "proven leak-proof."
- That the consumer integrations (`pramana#4`, `kathai-chithiram#12`) were inspected. Their existence and provider paths are taken from ADR-026's 2026-06-30 amendment, not separately confirmed against those repos.

---

*Point-in-time review. `wegofwd-video` is admitted to the four-lens watch set as of this file. Companion files to follow:*
[development-pattern](wegofwd-video-development-pattern.md) · [practices](wegofwd-video-practices.md)
