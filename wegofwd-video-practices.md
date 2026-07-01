# wegofwd-video — Good & Bad Practices

**Reviewed:** 2026-07-01 (v1.0 — first practices catalogue, companion to `wegofwd-video-critique.md` and `wegofwd-video-development-pattern.md`)
**Reviewer:** Claude (Anthropic)
**Repo:** `wegofwd2020-hub/wegofwd-video` · HEAD `233f248` (v1.0.0, 4 commits 2026-06-30) · consumers pin `v0.1.2`
**Scope:** Catalogue of observable practices in the v1.0.0 source (741 prod LOC / 362 test LOC / 30 tests), with `🔧 How to Improve` for each gap.

---

## How to read this

- ✅ marks a **good practice** worth preserving and propagating.
- ⚠️ marks a **gap or risk** with a concrete remediation in a `🔧 How to Improve` block.
- 🔴 marks a **must-fix-before-broad-adoption** item.
- Priority hints (P0/P1/P2/P3) align with `wegofwd-video-critique.md`.

This library is genuinely disciplined. It was extracted deliberately (ADR-026), it deliberately mirrors `wegofwd-llm` for family consistency, and its core is a zero-dependency typed seam. Most gaps below are pre-broad-adoption maturity and shared-infra-governance items, **not** design errors.

---

## 1. Good practices

### ✅ Zero-dependency core with lazy, per-provider SDK imports

`pyproject.toml:22` declares `dependencies = []`. The Google SDK is an *optional extra* — `[project.optional-dependencies] veo = ["google-genai>=0.3"]` (`pyproject.toml:24-25`) — and `veo.py` imports it lazily inside `_make_client` (`veo.py:180-187`), raising `VideoConfigurationError` if the extra is absent rather than failing at import time. The net effect is exactly the design goal stated in the pyproject comment (`pyproject.toml:18-21`): the deterministic-renderer consumer (kathai-chithiram) pulls **nothing** — `local_render.py` imports only from `contract`/`errors` (`local_render.py:16-22`). This is the single most valuable property for a shared dep: a consumer only pays for the path it uses.

> *Worth keeping. Resist the temptation to promote `google-genai` to a hard dep for "convenience"; it would tax every consumer.*

### ✅ Contract is one frozen-dataclass file

`contract.py` defines `VideoCapabilities`, `Ingredient`, `Shot`, `VideoBrief`, `VideoRequest`, `VideoResult`, the `VideoProvider` ABC, and `VIDEO_CONTRACT_VERSION` in 127 lines — every dataclass `frozen=True` (`contract.py:26,39,49,64,76,90`). Adding a provider is implementing one ABC (`contract.py:108-127`) plus adding one `VideoProviderSpec` row. Consumers never branch on vendor.

### ✅ Registry + `VideoProviderSpec` + roles mirror wegofwd-llm for family consistency

`VideoProviderSpec` (`registry.py:34-43`), `VIDEO_PROVIDER_REGISTRY` (`registry.py:46-105`), `ROLE_DEFAULTS` (`registry.py:109-113`), and `provenance()` (`registry.py:149-164`) are shaped one-for-one against `wegofwd_llm`. `resolve_role("narrative-video") -> ("veo", "veo-3.1")` (`registry.py:110`) keeps model ids in exactly one place with one update policy — app code never hardcodes a model string. A developer who knows one library knows the other; a maintenance pattern learned once applies twice.

### ✅ Ruff config deliberately mirrors the family

`pyproject.toml:34` says it outright: *"mirrors wegofwd-llm so a file passes lint identically across the family."* The select set `["E","W","F","I","B","C4","UP","S","T20","RUF"]` (`pyproject.toml:40`) is identical to the sibling. A file moved between family repos lints the same way — no per-repo lint drift.

### ✅ Allow-list enforced BEFORE provider construction

`build_provider` calls `validate_selection(provider_id, model, allowed=allowed)` as its first line (`registry.py:204`), and `validate_selection` raises `VideoNotAllowedError` before any provider object exists (`registry.py:136-137`). An excluded provider can't even attempt a vendor call. `test_allowlist.py:31-33` locks this in: `build_provider("veo", ..., allowed={"deterministic-renderer"})` raises before construction.

### ✅ `assert_brief_within_capabilities()` is a pre-dispatch gate that reports every violation at once

`registry.py:167-185` checks resolution, aspect, duration, and ingredient count against the spec's `VideoCapabilities`, accumulates **all** failures into `problems`, and raises one `VideoCapabilityError` listing every violation (`registry.py:184-185`). A caller fixing a brief sees all four problems in one round-trip, not one-at-a-time. `test_capabilities.py:13-20` asserts both duration and ingredient violations surface in a single message.

### ✅ Key-leak discipline is real *and* regression-tested

The security posture is layered and each layer is observable:
- `raise self._map_error(exc) from None` (`veo.py:145`) breaks the exception chain so an underlying SDK exception's `repr()` can't ride up.
- `_map_error` branches on an HTTP *code* (`code` / `status_code` / `response_status`), never the exception string (`veo.py:189-207`) — the comment at `veo.py:193-195` states the intent explicitly.
- `asset_bytes` and `raw` are `field(..., repr=False)` on `VideoResult` (`contract.py:97,105`), keeping payloads out of incident logs.
- `api_key` is validated non-empty before any call, in both the factory (`registry.py:221-222`) and the provider `__init__` (`veo.py:80-81`).

Crucially, `test_providers.py:207-209` (`test_no_key_in_repr`) asserts the key never appears in the provider's `repr()`, and `test_providers.py:171-193` asserts a 403-mapped error is key-free (`"super-secret" not in str(ei.value)`). **This is the exact regression guard `wegofwd-llm` was criticized for lacking** — the video library shipped it from day one.

### ✅ Honest registry — verification status is not overclaimed for placeholders

`runway` and `kling` are registered but openly marked `# UNVERIFIED` on base_url and model (`registry.py:84-85,94-95`), and `test_registry.py:49-52` asserts both carry `model_verified is False`. `test_versioning.py:19-24` asserts provenance for `kling` reports `model_verified: False` — "provenance must not claim otherwise." The honesty convention from wegofwd-llm carried over.

### ✅ Provenance stamps seed for reproducibility

`provenance()` includes `"seed": seed` (`registry.py:163`) alongside provider/model/versions, and `VideoRequest.seed` is documented as "required once a unit is APPROVED" (`contract.py:86`). `VeoProvider.generate` threads the seed into the SDK config (`veo.py:111-112`) and back into `VideoResult.seed` (`veo.py:157`). A stored asset can be re-derived from its stamp.

### ✅ Deterministic-renderer via callable injection keeps heavy/product code in the consumer

`CallableRenderProvider` wraps a caller-supplied `render_fn` (`local_render.py:25-48`) and `build_provider` requires it for `deterministic-renderer`, raising if absent (`registry.py:207-216`). kathai-chithiram's matplotlib/blender renderer stays in kathai; only the interface lives here (ADR-026 D4). This is what lets child content never leave the caller's process — no key, no vendor (`local_render.py:9`). `test_providers.py:37-55` proves the caller's fn actually runs.

### ✅ Tests use fake SDK clients — no live network

The Veo live path is exercised end-to-end with an injected `_FakeClient` (`test_providers.py:140-161`) driving submit→poll→download over two forced poll iterations. `VeoProvider.__init__` accepts an injectable `client` (`veo.py:78,91`) precisely so the SDK import is bypassed in tests. `build_request` and `render_brief_text` are pure and unit-tested without any client (`test_providers.py:84-98`, `196-204`).

### ✅ Demand-driven versioning

`requires-python = ">=3.10"` was lowered in v0.1.1 specifically because kathai-chithiram (a 3.10 consumer) surfaced a real constraint — documented inline at `pyproject.toml:10-13`. The floor moved in response to an actual second consumer, "exactly as ADR-026 D7 anticipated," not speculatively.

---

## 2. Bad practices / risks

### 🔴 `model_verified=True` for Veo despite no live run — the registry contradicts its own docstring (P1)

This is the sharpest gap, and it is stronger than the "still false" framing in the review brief. The **code sets** `model_verified=True` for Veo (`registry.py:63`), and both `test_registry.py:24` (`spec.model_verified is True`) and `test_versioning.py:12` (provenance `model_verified: True`) assert it. Yet:
- The module docstring says to *"flip model_verified after the first real generation"* and that Veo is *"NOT yet live-tested from our stack"* (`registry.py:10-12`).
- The README says the Veo live call is wired but *"a first real generation is still pending, so `veo` `model_verified` stays docs-verified until then"* (`README.md:90`).
- `veo.py:14-17` confirms the STATUS: *"once a first generation succeeds end-to-end, flip the registry's `model_verified` to a live-tested basis."*

So the flag is already `True` on a **docs-only** basis, and every asset's provenance stamp will claim `model_verified: True` even though no Veo generation has ever run from this stack. The whole point of the flag — letting downstream tooling detect assets made by an unverified integration — is defeated: it can never distinguish "docs-verified" from "live-verified."

🔧 **How to Improve:** decide what the flag means and make it truthful. Either (a) run one real Veo generation and legitimately keep it `True` (preferred — see §3), or (b) set `model_verified=False` until that run and flip it in the same commit as the live-smoke evidence, or (c) split the axis so provenance can't overclaim:

```python
@dataclass(frozen=True)
class VideoProviderSpec:
    ...
    docs_verified: bool = False   # capabilities/base_url checked against vendor docs
    live_verified: bool = False   # a real generation has succeeded from our stack
```

Then `provenance()` stamps both, and a consumer auditing assets can filter on `live_verified`.

### ⚠️ No in-repo CI — lint and tests rely entirely on consumer CI (P1)

There is no `.github/workflows/`. The 30 tests and the ruff config are only ever run by a developer locally or by whichever consumer happens to install a given SHA. For a library the README itself calls "the conformance gate — travels with the code" (`README.md:80`), nothing *runs* that gate on push. A commit that breaks a test or a lint rule can land on `main` unnoticed until a consumer's CInext catches it (or doesn't, since consumers pin `v0.1.2`).

🔧 **How to Improve:** add a minimal `.github/workflows/ci.yml` (P1, ~15 lines) — see §3 item 1. This is the single cheapest high-value fix.

### ⚠️ No `.watch/` mechanism though this is now a portfolio-level shared dependency (P1)

`wegofwd-llm` ships a `.watch/` mechanism to notify consumers of changes; `wegofwd-video` has none. With two live consumers (pramana on `veo`, kathai on `deterministic-renderer`) pinning versions, there's no signal path to tell them a new version exists or that the contract moved.

🔧 **How to Improve:** mirror wegofwd-llm's `.watch/` mechanism so the family's change-notification pattern is consistent (P1).

### ⚠️ Two of four registered providers are untested placeholders (P2)

`runway` and `kling` are in the registry (`registry.py:82-104`) with UNVERIFIED base_url/model, and no provider class exists for either — `build_provider` falls through to `raise VideoConfigurationError(f"no constructor wired for provider {provider_id!r}")` (`registry.py:231`). They are honestly marked (good), but they inflate `available_providers()` (`registry.py:116-124`) — a picker endpoint will offer `runway`/`kling` to an author, who then hits a construction error. There is no test asserting the "no constructor wired" path, either.

🔧 **How to Improve:** filter unbuilt providers out of `available_providers()` (mirror the `available: bool` pattern proposed for wegofwd-llm's gemma DOA entry), and add one test that `build_provider("runway", api_key="k")` raises the wired-constructor error. See §3 item 4.

### ⚠️ The Veo live path has never run — all coverage is against a fake client (P1)

Every Veo assertion goes through `_FakeClient` (`test_providers.py:140-161`). Nothing has validated the real `google-genai` `generate_videos` / `operations.get` / `files.download` surface (`veo.py:131,168,177`) against the actual SDK. Model deprecation, base_url drift (`registry.py:52`), or a `GenerateVideosConfig` field-name change would not be caught here — the exact class of bug that bit wegofwd-llm's Gemini path. Tied to the `model_verified` contradiction above.

🔧 **How to Improve:** a gated live-smoke job (see §3 item 3) that issues one minimum-cost Veo generation when an org secret is present.

### ⚠️ Reference-image / Ingredients contract surface is aspirational (P2)

`VideoBrief.ingredients` (`contract.py:73`), the `Ingredient` dataclass (`contract.py:39-46`), and `VideoCapabilities.reference_images=4` for Veo (`registry.py:59`) all model a feature that is **not wired**. `VeoProvider.generate` raises `VideoConfigurationError` the moment a brief carries ingredients (`veo.py:123-127`), and `test_providers.py:164-168` (`test_veo_generate_rejects_ingredients_until_wired`) asserts it *stays* unwired. So part of the public contract advertises a capability the only AI provider refuses. `render_brief_text` even flattens ingredients into prompt text (`veo.py:49-50`) that `generate` then rejects — a reader could reasonably assume it works.

🔧 **How to Improve:** either wire Ingredients-to-Video (resolve the ref pointers to image bytes/handles and pass them through), or guard the contract surface so it can't be constructed against a provider that will reject it — e.g. document the gap in the `Ingredient` docstring and add a capability note that `reference_images` is *declared* but not yet *dispatchable* for Veo. See §3 item 5.

### ⚠️ `license = "Proprietary"` on a repo shared across the family (P1)

`pyproject.toml:16` sets `license = { text = "Proprietary" }` — the same contradiction flagged for wegofwd-llm. A repo the README frames as a shared family library (`README.md:6-8`), distributed via `git+https` and pinned by multiple consumers, carries a proprietary license and no `LICENSE` file in the tree. This is legally ambiguous for any reader and friction-creating for a would-be internal contributor.

🔧 **How to Improve:** make one decision and propagate it (private + org-token distribution, or a permissive family license), and add a `LICENSE` file. See §3 item 6.

### ⚠️ No retry / failover policy in-package (P2 — defensible, but undocumented)

`errors.py:31-32` annotates `VideoRateLimitError` as *"Retryable / failover candidate"* but no policy lives in the package. Given generation is a long-running submit-poll-download op run inside the caller's own worker (`contract.py:110-114`), pushing retry to the caller is *defensible* — but it isn't stated anywhere a consumer will read it, and every consumer will reinvent it.

🔧 **How to Improve:** document the "no in-package retry; wrap in your own queue" contract in the README's rules block, and note the async/queue posture (pramana=Celery, kathai=subprocess, per `README.md:25-26`). Optionally sketch (don't build) a `RetryPolicy` Protocol as wegofwd-llm's critique proposes, kept opt-in.

### ⚠️ No CHANGELOG / SECURITY.md (P2)

The library handles BYOK vendor keys and its whole security story is the key-leak discipline in §1 — yet there is no `SECURITY.md` stating the BYOK/no-source/no-chain rules or a disclosure path, and no `CHANGELOG.md` despite the versioning story (`v0.1.0 → v1.0.0`) that consumers are asked to pin and upgrade deliberately (`README.md:84-91`).

🔧 **How to Improve:** add both, backfilling the existing versions in Keep-a-Changelog format, mirroring the templates in wegofwd-llm's critique.

### ⚠️ `git+https` distribution — every uncached consumer CI rebuilds from GitHub (P2)

Consumers pin `git+https://.../wegofwd-video@v0.1.2` (there is no PyPI/registry release). Every CI run that doesn't cache the install pulls source from GitHub, and there's no immutable artifact. Same gap flagged for wegofwd-llm.

🔧 **How to Improve:** wire a release-on-tag workflow to a private package registry so consumers pin `wegofwd-video==1.0.0` and CI caches the wheel.

### ⚠️ Scaffolding duplication with wegofwd-llm (registry / provenance / errors) — flagged by ADR-026 itself (P3)

`registry.py`, `errors.py`, and the provenance/versioning machinery are near-mechanical copies of wegofwd-llm's equivalents (the docstrings say "Mirrors wegofwd_llm/..." at `registry.py:6`, `errors.py:7`, `contract.py:10`). ADR-026 itself flags a future `wegofwd-core` to hold the shared scaffolding. Today the duplication means a fix to the registry/provenance pattern must be applied in two places.

🔧 **How to Improve:** make an explicit call — either extract `wegofwd-core` (registry base, provenance, error base, spec dataclass) once a third family member appears, or consciously accept the duplication and note it, so it isn't re-litigated each review. See §3 item 7.

---

## 3. How to improve (ranked)

**1. Add a minimal in-repo CI (P1, ~15 min).** The cheapest fix with the highest leverage — the "conformance gate" should run on every push.

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }   # test the floor
      - run: pip install -e ".[dev,veo]"
      - run: ruff check .
      - run: pytest
```

**2. Fix the `model_verified` contradiction (P1).** Split `docs_verified` / `live_verified` on `VideoProviderSpec` (or set the flag `False` until a real run), so provenance can't stamp `model_verified: True` for an integration that has never generated an asset. Update `test_versioning.py:12` and `test_registry.py:24` accordingly. This restores the flag's entire purpose.

**3. Run one real Veo generation and flip the flag on live evidence (P1).** Add a gated `live-smoke.yml` job that runs a minimum-cost `generate()` when an org secret is present; on success, flip `live_verified=True` in the same commit. This closes both the "never run live" gap and the flag contradiction at once.

```yaml
smoke-veo:
  if: ${{ secrets.SMOKE_VEO_KEY != '' }}
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - run: pip install -e ".[dev,veo]"
    - run: python -m wegofwd_video.smoke --provider veo
      env: { SMOKE_VEO_KEY: ${{ secrets.SMOKE_VEO_KEY }} }
```

**4. Add the `.watch/` mechanism and filter unbuilt providers from `available_providers()` (P1/P2).** Mirror wegofwd-llm's `.watch/` now that this is a portfolio-level shared dep. Add an `available: bool` (or reuse `live_verified`) to `VideoProviderSpec` and have `available_providers()` (`registry.py:116-124`) hide `runway`/`kling` from the picker until a constructor is wired — plus one test on the `no constructor wired` path (`registry.py:231`).

**5. Resolve the Ingredients aspiration (P2).** Either wire Ingredients-to-Video in `VeoProvider.generate` (`veo.py:119-127`), or explicitly mark `VideoCapabilities.reference_images` as *declared-not-dispatchable* for Veo in the docstring and README so a caller can't assume the `Ingredient` contract works end-to-end.

**6. Resolve the Proprietary-vs-shared license (P1).** Make one decision, add a `LICENSE` file, and align `pyproject.toml:16` with the repo's actual distribution model.

**7. Add CHANGELOG + SECURITY.md, document the async/queue posture, and decide on `wegofwd-core` (P2/P3).** Backfill the changelog, ship a short BYOK security policy, add a "no in-package retry — wrap in your own worker" note to the README rules, and record an explicit accept-duplication-or-extract decision so the scaffolding overlap with wegofwd-llm isn't re-argued each review.

---

## 4. Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  wegofwd-video — Practice Scorecard (v1.0, 2026-07-01, HEAD 233f248)  │
├─────────────────────────────────────┬───────────────┬────────────────┤
│  Discipline                         │  Current      │  Note           │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Zero-dep core / optional extras    │  Excellent    │  kathai pulls   │
│                                     │               │  nothing        │
│  Contract design                    │  Excellent    │  127-line file; │
│                                     │               │  frozen classes │
│  Family consistency (registry/roles)│  Excellent    │  mirrors llm    │
│  Key-leak discipline + regression   │  Excellent    │  the test llm   │
│  test                               │               │  was missing    │
│  Capability pre-dispatch gate       │  Excellent    │  reports all    │
│                                     │               │  violations     │
│  Registry honesty (placeholders)    │  Strong       │  UNVERIFIED     │
│                                     │               │  marked + tested│
│  Test mocking discipline            │  Strong       │  fake SDK; no   │
│                                     │               │  live network   │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  model_verified truthfulness        │  Contradiction│  True on docs   │
│                                     │  (P1)         │  basis; never   │
│                                     │               │  ran live       │
│  In-repo CI                         │  Absent (P1)  │  gate never runs│
│  .watch/ change-notification        │  Absent (P1)  │  llm has it     │
│  Veo live-smoke                     │  Absent (P1)  │  fake-only cover│
│  License / shared-repo coherence    │  Contradiction│  Proprietary +  │
│                                     │  (P1)         │  family-shared  │
│  Ingredients contract surface       │  Aspirational │  advertised,    │
│                                     │  (P2)         │  refused        │
│  runway/kling placeholders          │  Untested     │  inflate picker │
│                                     │  (P2)         │                 │
│  Retry/queue posture docs           │  Absent (P2)  │  defensible,    │
│                                     │               │  unstated       │
│  CHANGELOG / SECURITY.md            │  Absent (P2)  │  public hygiene │
│  PyPI / registry release            │  git+https    │  CI rebuilds    │
│                                     │  only (P2)    │  from GitHub    │
│  wegofwd-core scaffolding overlap   │  Duplicated   │  ADR-026 flags  │
│                                     │  (P3)         │  it             │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Overall library health             │  Strong + pre-│  Disciplined    │
│                                     │  adoption     │  seam; needs    │
│                                     │  polish       │  CI + one live  │
│                                     │  needed       │  run + governance│
└─────────────────────────────────────┴───────────────┴────────────────┘
```

The headline: **the design and test discipline are both strong — the video library even shipped the key-leak regression test its sibling was criticized for lacking** — and the remaining gaps are shared-infra governance (CI, `.watch/`, license, release) plus one honesty bug (`model_verified=True` before any live run). None require redesign; all are short, mostly mechanical fixes.

---

*Companion files: [critique](wegofwd-video-critique.md) · [development-pattern](wegofwd-video-development-pattern.md) · [cost](wegofwd-video-cost.md).*
