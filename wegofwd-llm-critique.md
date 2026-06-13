# wegofwd-llm — Code Review & Critique

**Reviewed:** 2026-06-13 (v1.0 — first review, top-level-watch admission to the critique suite)
**Repo:** `wegofwd2020-hub/wegofwd-llm` (public) · cloned to `/tmp/wegofwd-llm` for this pass
**HEAD:** `4823606` — *"fix(gemini): default to gemini-2.5-flash (verified live) → v0.1.2"* (2026-06-09)
**Phase:** Pre-1.0 library, **already load-bearing** for the portfolio
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue

---

## Why this project gets top-level watch

`wegofwd-llm` is the shared **multi-provider LLM seam** for the WeGoFwd2020 product family. As of 2026-06-13 it is consumed by:

- **StudyBuddy_OnDemand** — backing the Anthropic + OpenAI + Gemini pipeline paths after PRs #430/#431 ("back anthropic+openai with the shared wegofwd-llm package", "migrate google onto wegofwd-llm's gemini — finish ADR-012 consolidation").
- **StudyBuddy_SelfLearner (Mentible)** — the project from which it was extracted (`StudyBuddy_SelfLearner/pipeline/providers/` @ `main@2649101`).
- **Kathai Chithiram** — per `PRODUCT_CATALOG.md` lines 108–109, the parent-story → scene-script pipeline runs through `wegofwd-llm`.

This means a regression in `wegofwd-llm` is not a regression in one product — it is a portfolio incident. The library has 3 commits and 778 source LOC; the blast radius is the entire engine lineage. That asymmetry is the watch case.

---

## Executive Summary

`wegofwd-llm` is a small, disciplined, well-shaped library: a typed provider-agnostic contract (`LLMRequest` / `LLMResponse` / `Capabilities` / `Provider`), a registry of 9 providers (Anthropic native + 8 OpenAI-compat), a schema-agnostic validate→repair conformance loop, and a typed error hierarchy designed so SDK exceptions never chain upward (key-leak prevention). Three commits in source; clean Python; CI in place. The design rules are exemplary: **the package never sources keys** (caller passes BYOK) and **no key ever leaks** (every SDK call uses `raise ... from None` to prevent exception-chaining from stringifying request material). Three-axis versioning (package semver / `LLM_CONTRACT_VERSION` / per-provider `integration_version`) is real and stamped into `provenance()`, so a generated artefact knows which seam produced it.

The risks are the consequences of being early and being small. **Four of the nine registered providers carry `UNVERIFIED` model defaults in source** (`openai/gpt-4o-mini`, `deepseek/deepseek-chat`, `qwen/qwen-max`, `gemma/gemma-2-27b-it`) and `gemma` ships with `base_url=""`, which makes it dead on arrival — `build_provider("gemma", ...)` raises `LLMConfigurationError` at the `if not base_url:` guard. The error is loud and key-free, but the registry entry is misleading. The package is **sync-only** (`httpx.Client`, not `AsyncClient`) — async consumers (StudyBuddy's FastAPI request path) must run it in an executor; this is not stated in the README. The typed errors (`LLMRateLimitError`, `LLMTimeoutError`) are explicitly marked "Retryable / failover candidate" in `errors.py`, but **no actual retry / failover / circuit-breaker policy lives in the package** — every consumer must write its own. Distribution is `git+https://github.com/wegofwd2020-hub/wegofwd-llm@v0.1.x`, not PyPI; SelfLearner is currently pinned at `v0.1.0` while the package is at `v0.1.2` (already flagged by `studybuddy-selflearner-critique.md` v2.0). The license string is `Proprietary` in `pyproject.toml` while the GitHub repo is `public` — that contradiction wants resolving before an outside reader notices.

There are zero `TODO`/`FIXME`/`XXX` in source. 48 tests across 6 test files cover registry, conformance, allowlist, versioning, and both provider classes. None hit live APIs (correct). What's missing: a contract test that pins each registered provider's actual behaviour (live, gated by an env flag), and at least one test of the repair-prompt format itself. Both are pre-1.0 hardening, not blockers.

---

## Snapshot

| Metric | Value |
|---|---|
| Commits on `main` | 3 (initial extract + py.typed marker + Gemini default fix) |
| HEAD | `4823606` (2026-06-09, tagged v0.1.2) |
| Released versions | v0.1.0 → v0.1.1 (PEP 561 `py.typed`) → v0.1.2 (Gemini default) |
| Python source LOC | 778 across 6 modules + `__init__.py` |
| Test LOC | 620 across 6 test files |
| Test functions (`def test_`) | 48 |
| Providers in registry | 9 (1 native: anthropic · 8 OpenAI-compat) |
| Providers with `model_verified=True` | 4 of 9 (anthropic, groq, openrouter, gemini) |
| Providers with `UNVERIFIED` model defaults | 4 (openai, deepseek, qwen, gemma) |
| Providers dead-on-arrival | 1 (gemma — empty `base_url`) |
| TODO / FIXME / XXX in source | 0 |
| CI present | ✅ `.github/workflows/ci.yml` |
| Distribution | git+https (no PyPI) |
| Optional extras | `anthropic` (SDK), `dev` (pytest, pytest-asyncio, ruff, anthropic) |
| Python required | `>=3.11` |
| Current production consumers | StudyBuddy_OnDemand · StudyBuddy_SelfLearner · Kathai Chithiram |

---

## 1. Architecture

### Strengths

- ✅ **The contract is the seam.** `contract.py` defines `LLMRequest`, `LLMResponse`, `Capabilities`, and the `Provider` ABC as a tight, frozen-dataclass surface. Adding a provider is implementing one ABC and adding a `ProviderSpec` row; consumers never branch on vendor.
- ✅ **Registry is the only place model ids live.** `ROLE_DEFAULTS` maps logical roles (`authoring`, `toc`, `fast-draft`) to `(provider, model)` pairs. Application code never hardcodes a model string. This is the right shape for the consolidation work the StudyBuddy migration PRs just did.
- ✅ **Provenance is first-class.** `provenance()` returns `{provider, model, model_verified, integration_version, contract_version}` — a stampable record meant to ride on every generated artefact. The `model_verified` flag is a real "known unknown" indicator (not just a comment).
- ✅ **Three independent versioning axes.** Package semver / `LLM_CONTRACT_VERSION` / per-provider `integration_version`. Documented in the README (ADR-012 D4); enforced via the registry. This is unusual rigour for a v0.1.x library and is what makes content-vs-model audits possible downstream.
- ✅ **Schema-agnostic conformance.** `generate_validated` takes a caller-supplied `validate(text) -> parsed` callable that raises on invalid output. The package carries no product schema (lessons, units, compliance docs all reuse it).
- ✅ **Two clear non-negotiables in the README and enforced in code.** Rule 1: "The package never sources keys" — every constructor takes `api_key=` and `if not api_key: raise LLMConfigurationError(...)`. Rule 2: "No key ever leaks" — every SDK / HTTP exception path uses `raise LLMError(...) from None` (not `from exc`).

### Gaps & Risks

- ⚠️ **No retry / failover / circuit-breaker policy in-package.** `errors.py` annotates `LLMRateLimitError` as "Retryable / failover candidate" and `LLMTimeoutError` is similarly classified, but no policy implementation lives in the package. Each consumer must independently decide what to do on a 429. For shared infrastructure, this is the most consequential omission — a portfolio-wide rate-limit policy is half the point of having a seam.
- ⚠️ **Sync-only API.** `provider.generate()` is synchronous; `OpenAICompatibleProvider` uses `httpx.Client`, not `AsyncClient`. Async consumers (StudyBuddy backend FastAPI request path; SelfLearner job runner) must `run_in_executor` or wrap in `BackgroundTask`. The README doesn't mention this. An `AsyncProvider` peer or async overload is the natural v0.2 ask.
- ⚠️ **Anthropic tool-use silent fallback.** `AnthropicNativeProvider._extract` looks for a `tool_use` block first (the forced-JSON path); if absent, it falls through to a `text` block and returns prose. The caller receives a string that may not parse — `generate_validated` will catch it, but a consumer not using the conformance loop would silently get prose where JSON was requested. A `tokens_estimated`-style flag or strict-mode raise would close this.
- ⚠️ **`gemma` is dead-on-arrival in the registry.** `ProviderSpec(base_url="")` for gemma means `OpenAICompatibleProvider.__init__` raises `LLMConfigurationError("gemma provider requires a base_url")` at construction. Loud failure is good; a registry entry that can never succeed is misleading. Either remove the entry until it's wired, mark it `available=False`, or make `available_providers()` filter on validity.
- ⚠️ **No structured logging or metrics hook.** A shared seam is the natural place to centralise token-usage metering, attempt counts, and validator-repair rates. Today every consumer must instrument independently. A pluggable observer interface (e.g. `Provider.generate(..., observer=None)`) would let consumers attach Prometheus / Datadog / structured-log emitters without forking.

---

## 2. Code Quality

### Strengths

- ✅ **PEP 561 typed.** `wegofwd_llm/py.typed` ships in the wheel (`hatch.build.targets.wheel`). Consumers get `mypy`/`pyright` type-checking against the public surface. Added in v0.1.1 (commit `5db7c02`) — explicit packaging fix, not assumed.
- ✅ **Frozen dataclasses with explicit slots semantics.** `Capabilities`, `LLMRequest`, `LLMResponse`, `ProviderSpec`, `ConformanceResult` all `frozen=True`. `LLMResponse.raw: object | None = field(default=None, repr=False)` excludes the raw payload from `repr()` — small thing, useful in incident logs.
- ✅ **Domain-specific exception hierarchy.** `LLMError → LLMConfigurationError / LLMNotAllowedError / LLMAuthError / LLMRateLimitError / LLMTimeoutError / LLMResponseError → LLMSchemaError`. The taxonomy enables typed routing (a `LLMRateLimitError` is failover-eligible; a `LLMConfigurationError` is not).
- ✅ **`raise ... from None` is everywhere.** Both providers; the registry's `resolve_role`; every error path. This is the discipline that closes the key-leak surface.
- ✅ **Capability gating is real.** `OpenAICompatibleProvider._response_format` consults `self.capabilities.json_object` and `self.capabilities.json_schema` before adding a `response_format` field — so a request to a provider that doesn't support structured outputs silently falls through to prompt-only JSON rather than being rejected by the vendor.
- ✅ **`max_output_tokens` clamping for free tiers.** Groq's free tier rejects > 12k output tokens with HTTP 413; `OpenAICompatibleProvider.generate` clamps `req.max_tokens` down to `capabilities.max_output_tokens` when set. Documented in code with the actual incident reason. This kind of "the right comment in the right place" is high-signal.
- ✅ **Ruff config mirrors consumer projects.** `pyproject.toml` `[tool.ruff]` selects `E W F I B C4 UP S T20 RUF` — same shape as StudyBuddy/SelfLearner — so a file passes lint identically here and in any consumer. Removes a class of "passes one repo, fails the other" friction.
- ✅ **Zero `TODO`/`FIXME`/`XXX` in source.** Verified by grep.

### Gaps & Risks

- ⚠️ **One docstring drift.** `openai_compatible.py:1-12` says the api_key "is NEVER placed in... the `LLMResponse.raw` payload" — but `generate()` does set `raw=data`. The intent is correct (the vendor's response payload doesn't include the request key), but the wording could mislead a future reader. Tighten to "the api_key is never placed in raw or in an exception; raw stores the vendor's response JSON for debug only."
- ⚠️ **No `model_verified` enforcement at build time.** `provenance()` stamps the flag, but `build_provider()` happily constructs a provider whose model is `UNVERIFIED`. A `strict=True` flag (or env-gated warning) would let consumers refuse to call an unverified model in production.
- ⚠️ **Conformance `max_repairs` is global.** The default of 2 might be wrong per-provider — Anthropic tool-use almost never needs repair; a free-tier Gemma call might want zero (each repair costs another token budget). A per-provider `repair_budget` in `Capabilities` would make this tunable.
- ⚠️ **`_repair_prompt` echoes `bad_text[:4000]`** verbatim into the next request. For an extremely long prompt, two repair rounds add ~12k input tokens that the caller didn't budget for. Document the cost; consider truncating the echo per-provider.

---

## 3. Test Coverage

### Strengths

- ✅ **48 tests over 6 files, no live APIs.** `test_registry.py` (7), `test_versioning.py` (6), `test_allowlist.py` (12), `test_conformance.py` (4), `test_anthropic_native.py` (8), `test_openai_compatible.py` (11). Anthropic is mocked via an injected client; OpenAI-compat is exercised against `httpx.MockTransport`. Both are correct shapes for SDK-mocked unit tests.
- ✅ **`pytest-asyncio` in dev extras with `asyncio_mode = "auto"`** — async tests work without per-function decorators. Future-proofs the test suite for an `AsyncProvider` peer.
- ✅ **CI exists.** `.github/workflows/ci.yml` is present. (Not opened in this pass; checked existence only.)

### Gaps & Risks

- ⚠️ **No contract / live-smoke test per provider.** A gated job that runs one real `generate({ prompt: "ping", max_tokens: 32 })` against each configured provider (only when its env-keyed token is present in the CI environment) would catch model deprecation and base-URL drift before a consumer does. Gemini-2.0-flash hit free-tier quota and 1.5 was retired (per the registry comment); only a live test reliably surfaces that.
- ⚠️ **No test of the repair-prompt format itself.** `_repair_prompt` is verbatim string formatting; if a future edit breaks the contract (model expects "Validation error:" prefix to know which line to fix), no test catches it. A snapshot test against a fixed input would lock the format.
- ⚠️ **No test of `model_verified` propagation through `provenance()`.** Easy to add — `test_registry.py` has the shape.
- ⚠️ **No coverage gate in CI** (assumption — not opened in this pass; if absent, add `--cov-fail-under=85` to match dronePrjs's discipline). Per-module coverage matters more for a library than a service.

---

## 4. Documentation

### Strengths

- ✅ **README is right-sized and accurate.** Three sections (What it is / Two rules / Versioning) plus install + use + test. The "Two rules that make it reusable" framing is exactly what a consumer needs to read in 60 seconds.
- ✅ **Module docstrings carry the *why*.** Every file opens with a paragraph that names the design choice (`contract.py`: "additive — the legacy tuple-returning `LLMProvider` in base.py is untouched until the backend rewire"; `anthropic_native.py`: "Anthropic's strongest structured-output path — tool-use"; `conformance.py`: "validate → repair loop ... instead of blind retries"). These are the comments worth writing.
- ✅ **ADR-012 cross-reference.** README points at the rationale doc in SelfLearner — anyone landing in the package can trace back to the design discussion.
- ✅ **Real incident notes in code.** `registry.py` "Free tier enforces a per-request/TPM token limit (~12k); 16384 → HTTP 413. Cap output so input+output stays under it. Verified 2026-06-07." and "gemini-2.5-flash — verified live 2026-06-09 (valid JSON, single attempt) via this OpenAI-compat path. 2.0-flash hit free-tier quota (429); 1.5 retired." This is the comment style other repos should imitate.

### Gaps & Risks

- ⚠️ **No `CHANGELOG.md`.** v0.1.0 → v0.1.1 → v0.1.2 changes are recoverable from git log + commit subjects, but a stable consumer-facing changelog is table stakes for "consumers pin a version and upgrade deliberately."
- ⚠️ **No `CONTRIBUTING.md` / `SECURITY.md`.** For a public repo handling secret material, a `SECURITY.md` describing the BYOK / no-env / no-chain rules and the responsible-disclosure path would protect users and reduce ambiguity for external scanners.
- ⚠️ **Sync-only fact is undocumented.** Async consumers need to know up front.
- ⚠️ **The "UNVERIFIED" markers are documented only inline.** A short "Providers — verification matrix" table in the README would make the 4-of-9 state visible at install time rather than after a 422 in production.
- ⚠️ **License contradiction.** `pyproject.toml` says `license = { text = "Proprietary" }`; the GitHub repo is `public`. Pick one: either change the license to permit the use cases the public repo invites, or change the repo to private and document the consumer-distribution model.

---

## 5. Security

### Strengths

- ✅ **BYOK is enforced at construction.** `if not api_key: raise LLMConfigurationError(...)` on both providers; the package will not silently fall back to an env var, a config file, or a default.
- ✅ **Key never leaves the instance.** Held as `self._api_key` (OpenAI-compat) and inside the injected SDK client (Anthropic). Not in `LLMResponse.raw`, not in `repr()` (raw is `repr=False`), not in module state.
- ✅ **Exception chaining is broken intentionally.** Every SDK / HTTP call wraps in `try/except Exception: raise LLMError(...) from None`. This is the specific mechanism that prevents `anthropic.AuthenticationError`'s `repr()` (which can stringify the request, including the key) from chaining into a log line.
- ✅ **Typed errors enable safe surfacing.** `LLMConfigurationError` → 4xx "unknown provider"; `LLMNotAllowedError` → 403 (allow-list violation); `LLMAuthError` → 401; `LLMRateLimitError` → 429. The API boundary can map without inspecting message strings.
- ✅ **Allow-list is enforced before construction.** `build_provider(..., allowed=[...])` raises `LLMNotAllowedError` *before* any provider is built — so an excluded provider can't even attempt a vendor call.

### Gaps & Risks

- ⚠️ **No test asserts the key-leak rule.** The rule is enforced by code review only. Add: a test that mocks the SDK to raise an exception whose `repr()` contains the api_key, then asserts the `LLMError` raised by the provider does not contain the key string. This is the rule's regression guard.
- ⚠️ **`base_url` in `LLMConfigurationError` messages is fine, but key-prefix shape-checks are not enforced.** `ProviderSpec.key_prefix` is documented but never validated — `build_provider("anthropic", api_key="gsk_...")` accepts the wrong-shape key and the vendor rejects it later with `LLMAuthError`. Cheap client-side validation against `key_prefix` would fail faster and not consume a vendor request.
- ⚠️ **`httpx.HTTPError` is mapped to generic `LLMError("transport error")`.** That's correct for key safety, but loses the distinction between "DNS failed" and "TLS failed" — both produce identical user-visible errors. A typed `LLMTransportError` subtree would help debugging without leaking request material.
- ⚠️ **No rate-limit / spend-cap budget.** The library has no notion of "this caller has consumed N tokens today; refuse further calls." For a shared seam where one consumer's runaway loop is a portfolio-wide problem, an in-process budget primitive (callable / counter) is worth at least sketching.

---

## 6. Scalability / Ops

### Strengths

- ✅ **Distribution is one `pip install`.** Optional `anthropic` extra is correctly modelled — managed/OpenAI-compat-only consumers don't pull the SDK.
- ✅ **No state, no warm-up.** A provider instance is created per request (BYOK) or pooled (managed). No global initialisation, no lazy module-level singletons. This is the right shape for serverless and per-worker FastAPI deploys alike.
- ✅ **Capability flags drive request shaping.** The `Capabilities` dataclass is the single switch for JSON-mode, system-prompt support, and per-provider output ceilings. Adding a provider is mostly filling out one row.

### Gaps & Risks

- ⚠️ **No PyPI release.** Consumers pin to `git+https://github.com/wegofwd2020-hub/wegofwd-llm@v0.1.2`. Every CI run that doesn't cache the install pulls source from GitHub. SelfLearner's critique (v2.0) already names this; flagging here because for a shared portfolio dep, a private PyPI (`pip-services` / GitHub Packages / CodeArtifact) would close it.
- ⚠️ **No release cadence / no `git tag` automation.** Three commits, three versions, each a manual tag. Pre-1.0 this is fine; once contract v2 lands, a `release.yml` (tag → wheel → registry) is a one-day investment that pays back forever.
- ⚠️ **Single-maintainer / single-architect risk.** The contract was designed and validated against StudyBuddy's needs, then extracted; SelfLearner is the second consumer; Kathai Chithiram is the third. Three consumers is the right point at which to (a) freeze the v1 contract or (b) accept the v2 break before the consumer set grows further. The personality-review pattern of "you are your own only architectural challenger" applies here in a particularly pointed way — every consumer is yours.

---

## 7. Priority Actions

Ranked by risk × leverage.

| # | Action | Why | Effort |
|---|---|---|---|
| 1 | **Resolve `gemma` registry entry** — either remove it, set `available=False`, or wire the actual `base_url`. | Dead config is a footgun even when it raises. | 30 min |
| 2 | **Document sync-only / async-consumer pattern in README.** | StudyBuddy and SelfLearner both hit this; future consumers will. | 30 min |
| 3 | **Resolve the `license = "Proprietary"` vs public-repo contradiction.** | Either re-license or re-private. Current state is friction at minimum, legal ambiguity at worst. | 1 h (decision) |
| 4 | **Add a key-leak regression test.** Mock the SDK to raise an exception whose `repr()` contains the api_key; assert the `LLMError` raised does not stringify it. | The hardest rule has zero test coverage. | 1 h |
| 5 | **Add a "providers — verification matrix" table to the README + `model_verified` strict mode in `build_provider`.** | 4 of 9 providers are `UNVERIFIED` and that fact is buried in code comments. | 2 h |
| 6 | **Add a per-provider live-smoke CI job, gated on env keys.** | Catches vendor model deprecation before a consumer does (Gemini 2.0-flash / 1.5 incidents already happened). | 1 day |
| 7 | **Sketch an observer / metrics hook on `Provider.generate`.** | Pluggable token-usage / repair-rate emission lets every consumer instrument without forking. | 1–2 days |
| 8 | **Sketch (don't yet build) a retry / failover policy contract.** | The errors are typed for it; the policy is missing; consumer copies are a portfolio fragility. v0.2 candidate. | Design: 1 day |
| 9 | **Move from `git+https` to a real package registry (private PyPI / CodeArtifact / GitHub Packages).** | Already-flagged by SelfLearner critique. Closes the every-CI-pulls-from-GitHub fragility. | 1 day |
| 10 | **Add `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.** | Public-repo hygiene; supports the "consumers pin and upgrade deliberately" promise. | 2 h |

---

## 8. Watch Cadence (recommendation)

Because `wegofwd-llm` is now load-bearing across at least three products, a watch loop is warranted. Suggested cadence — to be confirmed:

- **Weekly:** automated commit-delta check against `main`. Any commit ⇒ a small Claude sub-agent re-runs §7 against the diff and posts findings to a dated `wegofwd-llm-watch-YYYY-MM-DD.md` file in this repo. Quiet weeks produce a one-line "no change" note.
- **On every version bump:** automated full re-critique (re-runs sections 1–6, refreshes the Snapshot table). Posts a PR rather than committing directly.
- **On every consumer rev that bumps the `wegofwd-llm` pin:** the watch sub-agent checks the pin diff (e.g. SelfLearner `v0.1.0` → `v0.1.2`) and notes which behaviour changes the consumer is now exposed to.
- **Quarterly:** human review of the watch log + a "do we need a v0.2?" decision against the priority backlog.

The mechanism — `loop` skill, `schedule` skill, GitHub Actions cron, or a manual `gh` script — is a separate decision. See the question at the end of `README.md`'s changelog entry for v2.6.

---

## 9. Anti-claims

For honesty: this is a **first review based on the source at HEAD `4823606`**. The following are *not* asserted by this document:

- That `wegofwd-llm` is production-tested in every consumer. Verified-load-bearing in StudyBuddy_OnDemand (PRs #430/#431 merged) and SelfLearner (reviewed v2.0 already names it); Kathai Chithiram's use is per `PRODUCT_CATALOG.md` but not separately confirmed.
- That CI is green or that the test suite was re-run in this pass. CI workflow file presence was checked; tests were not executed live this pass.
- That the listed providers behave as the registry capability flags claim. The registry's `model_verified=True` is the package's own assertion; live verification per provider is the §7 #6 ask.
- That no key leak has occurred historically. The §5 #1 ask is to *guard against future leaks*; the absence of a test means the rule's track record is "no incident known," not "incident-free."

---

*This critique is a point-in-time review. wegofwd-llm is admitted to the four-lens watch set as of v2.6 of `project-critique`. Companion files (`-development-pattern.md`, `-practices.md`, `-cost.md`) to follow.*
