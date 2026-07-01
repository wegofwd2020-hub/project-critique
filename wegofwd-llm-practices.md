# wegofwd-llm — Good & Bad Practices

**Reviewed:** 2026-06-13 (v1.0 — first practices catalogue, companion to `wegofwd-llm-critique.md` and `wegofwd-llm-development-pattern.md`)
**Repo:** `wegofwd2020-hub/wegofwd-llm` · HEAD `4823606` (v0.1.2)
**Scope:** Catalogue of observable practices in the v0.1.2 source, with `🔧 How to Improve` for each gap.

---

## How to read this

- ✅ marks a **good practice** worth preserving and propagating.
- ⚠️ marks a **gap or risk** with a concrete remediation in a `🔧 How to Improve` block.
- 🔴 marks a **must-fix-before-1.0** item.
- Priority hints (P0/P1/P2/P3) align with `wegofwd-llm-critique.md` §7.

---

## 1. Architecture Practices

### ✅ Subtractive scope

The library names every concern it is **not** going to own — retry policy, failover, metering, async, secret sourcing, observer hooks — and pushes each back to the caller. This is what keeps it shared rather than coupled to any one consumer's policy choice.

> *Worth keeping. Documented as Rule 1 ("Library, not a service") in the README. Resist scope creep at every v0.2 review.*

### ✅ Contract is one frozen-dataclass file

`contract.py` defines `LLMRequest`, `LLMResponse`, `Capabilities`, `Provider`, and `LLM_CONTRACT_VERSION` in 96 lines. Adding a provider is implementing one ABC + adding a `ProviderSpec` row; consumers never branch on vendor.

### ✅ Logical-role pinning isolates model ids

`ROLE_DEFAULTS["authoring"] = ("anthropic", "claude-sonnet-4-6")`. Application code requests a role; the registry resolves to a model. Updating the "authoring" model is a one-line edit in one place.

### ✅ Provenance is a stamped contract, not a comment

`provenance()` returns a dict with `{provider, model, model_verified, integration_version, contract_version}`. Meant to ride on every generated artefact so downstream tooling can detect content made by an outdated integration.

### ⚠️ No in-package retry / failover / circuit-breaker policy (P1)

`errors.py` explicitly annotates `LLMRateLimitError` and `LLMTimeoutError` as *"Retryable / failover candidate"* — but no policy implementation lives in the package. Every consumer must independently decide.

🔧 **How to Improve:** sketch (don't yet build) a `RetryPolicy` Protocol in `contract.py`, threaded through `Provider.generate()` as an optional kwarg, with one reference implementation (e.g. `ExponentialBackoffPolicy(max_retries=3, base_delay_s=1.0, on=[LLMRateLimitError, LLMTimeoutError])`). Keep it opt-in — the default remains no retry — but ship one reference so consumers stop writing it independently.

```python
# contract.py — sketch
class RetryPolicy(Protocol):
    def attempt(self, callable_: Callable[[], LLMResponse]) -> LLMResponse: ...

# usage
provider.generate(req, policy=ExponentialBackoffPolicy())
```

### ⚠️ No observer / metrics hook (P2)

A shared seam is the natural place to centralise token-usage metering and validator-repair rates. Today every consumer must instrument independently.

🔧 **How to Improve:** add an optional `observer: Observer | None = None` argument to `Provider.generate()` (and `generate_validated()`):

```python
class Observer(Protocol):
    def on_request(self, req: LLMRequest, provider_id: str, model: str) -> None: ...
    def on_response(self, resp: LLMResponse, attempt: int) -> None: ...
    def on_error(self, exc: LLMError, attempt: int) -> None: ...
    def on_repair(self, original_error: Exception, attempt: int) -> None: ...
```

One reference observer that emits structured-log lines. Consumers wire Prometheus / Datadog / their own pipeline.

---

## 2. Code Quality Practices

### ✅ Frozen dataclasses everywhere

`Capabilities`, `LLMRequest`, `LLMResponse`, `ProviderSpec`, `ConformanceResult` — all `frozen=True`. `LLMResponse.raw: object | None = field(default=None, repr=False)` excludes the raw payload from `repr()` so it doesn't leak into incident logs.

### ✅ PEP 561 typed marker shipped

`wegofwd_llm/py.typed` is included in the wheel via `[tool.hatch.build.targets.wheel] packages = ["wegofwd_llm"]`. Consumers get strict typing against the public surface. Added in v0.1.1 as an explicit packaging fix (commit `5db7c02`).

### ✅ Ruff config mirrors consumers

`[tool.ruff] select = ["E", "W", "F", "I", "B", "C4", "UP", "S", "T20", "RUF"]` — identical to StudyBuddy_OnDemand and Mentible. A file passes lint identically here and in any consumer.

### ✅ `raise ... from None` is everywhere

Every SDK/HTTP error path uses `raise LLMError(...) from None`, never `from exc`. This is the discipline that prevents chained vendor exceptions from stringifying secret material.

### ✅ Capability gating drives request shaping

`OpenAICompatibleProvider._response_format` consults `self.capabilities.json_object` / `.json_schema` before adding a `response_format` field. A request to a provider that doesn't support structured outputs silently falls through to prompt-only JSON rather than being rejected by the vendor.

### ✅ Free-tier output clamping with the incident reason inline

```python
cap = self.capabilities.max_output_tokens
max_tokens = min(req.max_tokens, cap) if cap > 0 else req.max_tokens
```

The comment names the actual incident (Groq's free tier rejects >12k output tokens with HTTP 413). This is the kind of "right comment in the right place" worth imitating.

### ✅ Zero `TODO`/`FIXME`/`XXX` in source

Verified by grep across all six modules. The discipline carries from StudyBuddy and dronePrjs.

### ⚠️ Docstring drift in `openai_compatible.py` (P3)

The module docstring says the api_key "is NEVER placed in... the `LLMResponse.raw` payload" — but `generate()` does set `raw=data`. The *intent* is correct (the vendor's response payload doesn't include the request key), but the wording could mislead a future reader.

🔧 **How to Improve:** tighten the docstring:

```python
"""
Key handling (BYOK): the key is sent as a Bearer header per request and is held
only on the instance for the call's lifetime. It is NEVER placed in an exception
message. `raw` stores the vendor's response JSON for debug only — vendor
responses do not echo the request, so raw contains no key material.
"""
```

### ⚠️ Conformance `max_repairs` is global (P2)

Default of 2 might be wrong per-provider. Anthropic tool-use almost never needs repair; a free-tier Gemma call might want zero (each repair costs another token budget).

🔧 **How to Improve:** add a per-provider `repair_budget` to `Capabilities`, and have `generate_validated()` clamp `max_repairs` down to it:

```python
@dataclass(frozen=True)
class Capabilities:
    ...
    repair_budget: int = 2  # provider-recommended max validate→repair attempts
```

```python
def generate_validated(provider, req, validate, *, max_repairs: int = 2):
    effective = min(max_repairs, provider.capabilities.repair_budget)
    for attempt in range(1, effective + 2):
        ...
```

### ⚠️ `_repair_prompt` echoes `bad_text[:4000]` verbatim into the next request (P3)

For an extremely long prompt, two repair rounds add ~12k input tokens that the caller didn't budget for.

🔧 **How to Improve:** document the cost in the conformance docstring; consider exposing `max_echo` as a `Capabilities` field so a per-provider tighter cap is possible. Cheap; high-signal.

---

## 3. Test Coverage Practices

### ✅ 48 tests over 6 files, no live APIs

`test_registry.py` (7), `test_versioning.py` (6), `test_allowlist.py` (12), `test_conformance.py` (4), `test_anthropic_native.py` (8), `test_openai_compatible.py` (11). Anthropic via injected client; OpenAI-compat via `httpx.MockTransport`. Both are the correct shapes.

### ✅ `pytest-asyncio` already configured

`asyncio_mode = "auto"` — async tests work without per-function decorators. Future-proofs for an `AsyncProvider`.

### ✅ CI exists

`.github/workflows/ci.yml` runs the test suite. Not opened in this pass; existence verified.

### 🔴 No key-leak regression test (P1 — the hardest rule has zero coverage)

The "no key ever leaks" rule is enforced by `raise ... from None` everywhere, but **no test** mocks an SDK exception whose `repr()` contains the api_key and asserts the wrapped `LLMError` does not stringify it.

🔧 **How to Improve:** add `tests/test_no_key_leak.py`:

```python
import pytest
from wegofwd_llm import build_provider, LLMRequest
from wegofwd_llm.errors import LLMError

SECRET_KEY = "sk-ant-LEAKY-FAKE-KEY-FOR-TEST-12345"

class _LeakyClient:
    """A fake SDK client whose exceptions stringify the api_key — the worst case."""
    def __init__(self, api_key: str): self._api_key = api_key
    class _Messages:
        def __init__(self, key): self._key = key
        def create(self, **kwargs):
            raise RuntimeError(f"BOOM with Authorization=Bearer {self._key}")
    @property
    def messages(self): return self._Messages(self._api_key)

def test_provider_does_not_stringify_key_on_sdk_error():
    leaky = _LeakyClient(SECRET_KEY)
    provider = build_provider("anthropic", api_key=SECRET_KEY, model="claude-sonnet-4-6")
    provider._client = leaky  # injection for this test
    with pytest.raises(LLMError) as excinfo:
        provider.generate(LLMRequest(prompt="ping", max_tokens=32))
    # The wrapped LLMError must NOT contain the key.
    assert SECRET_KEY not in str(excinfo.value)
    assert SECRET_KEY not in repr(excinfo.value)
    # The chain must be broken (from None).
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None or SECRET_KEY not in repr(excinfo.value.__context__)
```

Repeat for `OpenAICompatibleProvider` with a `httpx.MockTransport` that raises an HTTPError whose `repr()` contains the key. This is the regression guard for the load-bearing security rule.

### ⚠️ No contract / live-smoke test per provider (P1)

A gated job that runs one real `generate(LLMRequest(prompt="ping", max_tokens=32))` against each configured provider (only when its env-keyed token is present in the CI environment) would catch model deprecation and base-URL drift before a consumer does. The Gemini 2.0-flash quota hit / 1.5 retirement is the exact class of bug a fixture cannot catch.

🔧 **How to Improve:** add `.github/workflows/live-smoke.yml` with separate jobs per provider, each gated on the presence of an org secret:

```yaml
jobs:
  smoke-anthropic:
    if: ${{ secrets.SMOKE_ANTHROPIC_KEY != '' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e ".[dev,anthropic]"
      - run: python -m wegofwd_llm.smoke --provider anthropic
        env:
          SMOKE_ANTHROPIC_KEY: ${{ secrets.SMOKE_ANTHROPIC_KEY }}
```

The smoke script lives in `wegofwd_llm/smoke.py` — issues one minimum-cost ping per provider, asserts non-empty text, exits non-zero on any other outcome.

### ⚠️ No test of the repair-prompt format itself (P3)

`_repair_prompt` is verbatim string formatting; if a future edit breaks the contract (model expects "Validation error:" prefix to know which line to fix), no test catches it.

🔧 **How to Improve:** add a snapshot test:

```python
def test_repair_prompt_format_is_stable():
    out = _repair_prompt(
        original="Write a JSON object with `name` and `age`.",
        error="missing required field 'age'",
        bad_text='{"name": "Alice"}',
    )
    assert "Validation error: missing required field 'age'" in out
    assert "Previous response (verbatim):\n{\"name\": \"Alice\"}" in out
    assert "Return ONLY corrected, valid JSON" in out
```

### ⚠️ No `--cov-fail-under` gate in CI (P2)

If absent (not opened this pass), add one. dronePrjs runs `--cov-fail-under=80`; for a library, ≥85% is reasonable.

---

## 4. Documentation Practices

### ✅ README is right-sized

Three sections (What it is / Two rules / Versioning) + install + use + test. The "Two rules that make it reusable" framing is exactly what a consumer needs to read in 60 seconds.

### ✅ Module docstrings carry the *why*, not the *what*

Every file opens with a paragraph naming the design choice. `anthropic_native.py`: *"Anthropic's strongest structured-output path — tool-use ... forcing a single tool with the caller's schema as the tool's input_schema is far more reliable than asking for JSON in prose."* This is high-signal commentary worth imitating.

### ✅ Real incident notes in code

The Groq 413 / Gemini quota notes in `registry.py` are not folklore — they cite verification dates and the actual HTTP status code. This is the right place for that kind of comment.

### ✅ ADR-012 cross-reference

The README points back to the rationale doc in Mentible. Anyone landing in the package can trace to the design discussion.

### ⚠️ No CHANGELOG.md (P2)

v0.1.0 → v0.1.1 → v0.1.2 changes are recoverable from `git log` + commit subjects, but a stable consumer-facing changelog is table stakes for *"consumers pin a version and upgrade deliberately."*

🔧 **How to Improve:** add `CHANGELOG.md` in Keep-a-Changelog format. Backfill the three existing versions; lock the convention going forward:

```markdown
# Changelog
All notable changes to wegofwd-llm. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.2] — 2026-06-09
### Fixed
- gemini default model bumped to gemini-2.5-flash (2.0-flash hit free-tier quota; 1.5 retired).

## [0.1.1] — 2026-06-05
### Fixed
- packaging: ship the PEP 561 py.typed marker so consumer mypy sees package types.

## [0.1.0] — 2026-06-04
### Added
- Initial extract from Mentible pipeline/providers (ADR-012).
- LLMRequest/LLMResponse/Capabilities/Provider contract (LLM_CONTRACT_VERSION = 1).
- Anthropic native (tool-use), OpenAI-compatible (raw httpx).
- 9 providers registered (anthropic, openai, groq, openrouter, gemini, deepseek, qwen, gemma).
- generate_validated validate→repair conformance loop.
- Typed error hierarchy; BYOK enforced at construction.
```

### ⚠️ No `SECURITY.md` (P1)

For a public repo handling secret material, a `SECURITY.md` describing the BYOK / no-env / no-chain rules and the responsible-disclosure path would protect users and reduce ambiguity for external security scanners.

🔧 **How to Improve:** ship a short `SECURITY.md`:

```markdown
# Security policy

## Threat model
wegofwd-llm processes BYOK API keys for vendor LLM providers. The library's
core security posture is encoded in two rules:

1. **The package never sources keys.** Every constructor requires `api_key=`;
   the library never reads env vars, files, vaults, or keyrings.
2. **No key ever leaks.** SDK / HTTP exceptions are mapped to typed `LLMError`
   subclasses via `raise ... from None`, breaking the chain so an underlying
   exception's repr cannot stringify the request.

## Reporting a vulnerability
Email security@<your-domain> with details. Do not file public issues for
security-sensitive findings.
```

### ⚠️ Sync-only is undocumented (P2)

Async consumers (FastAPI request paths, async job runners) must wrap with `run_in_executor`. The README doesn't mention this.

🔧 **How to Improve:** add a "Sync vs async" subsection to the README explaining the sync-only design and recommended async wrapper:

```python
# in your async FastAPI handler
from concurrent.futures import ThreadPoolExecutor
import asyncio

_executor = ThreadPoolExecutor(max_workers=8)

async def generate_async(provider, req):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, provider.generate, req)
```

### ⚠️ UNVERIFIED markers live only inline (P1)

`openai`, `deepseek`, `qwen`, `gemma` carry `# UNVERIFIED` comments on their default models in `registry.py` — but a consumer running `pip install wegofwd-llm` and reading the README will not see this. They will only discover it when a vendor returns 404 / 422.

🔧 **How to Improve:** add a "Providers — verification matrix" table to the README:

```markdown
## Providers — verification matrix

| Provider | Default model | Verified live | Notes |
|---|---|---|---|
| anthropic | claude-sonnet-4-6 | ✅ 2026-06-04 | Native, tool-use JSON |
| openai | gpt-4o-mini | ⚠️ UNVERIFIED | Update before production use |
| groq | llama-3.3-70b-versatile | ✅ 2026-06-07 | Free tier caps output at ~12k tokens |
| openrouter | meta-llama/llama-3.3-70b-instruct:free | ✅ 2026-06-05 | :free variants cap completion length |
| gemini | gemini-2.5-flash | ✅ 2026-06-09 | OpenAI-compat path; 2.0-flash deprecated |
| deepseek | deepseek-chat | ⚠️ UNVERIFIED | |
| qwen | qwen-max | ⚠️ UNVERIFIED | base_url also UNVERIFIED |
| gemma | gemma-2-27b-it | 🔴 DEAD ON ARRIVAL | base_url is empty in the registry |
```

This is the kind of fact that should be impossible to miss.

---

## 5. Security (BYOK) Practices

### ✅ BYOK enforced at construction

`if not api_key: raise LLMConfigurationError(...)` on both providers. The library will not silently fall back to an env var, a config file, or a default.

### ✅ Key never leaves the instance

Held as `self._api_key` (OpenAI-compat) or inside the injected SDK client (Anthropic). Not in `LLMResponse.raw`, not in `repr()` (raw is `repr=False`), not in module state.

### ✅ Allow-list enforced before construction

`build_provider(..., allowed=[...])` raises `LLMNotAllowedError` *before* any provider is built — so an excluded provider can't even attempt a vendor call.

### ✅ Typed errors enable safe HTTP mapping

`LLMConfigurationError` → 4xx "unknown provider"; `LLMNotAllowedError` → 403; `LLMAuthError` → 401; `LLMRateLimitError` → 429. The API boundary can map without inspecting message strings.

### 🔴 No key-leak regression test (P1)

See §3 above. This is the load-bearing rule with zero test coverage. Highest priority single missing test in the codebase.

### ⚠️ `key_prefix` documented but not enforced (P2)

`ProviderSpec.key_prefix` is set (`sk-ant-`, `gsk_`, `sk-or-`, `""` for Gemini) but never validated. `build_provider("anthropic", api_key="gsk_...")` accepts the wrong-shape key and the vendor rejects it later with `LLMAuthError`.

🔧 **How to Improve:** cheap client-side shape check in `build_provider`:

```python
def build_provider(provider_id, *, api_key, ...):
    ...
    spec = PROVIDER_REGISTRY[provider_id]
    if spec.key_prefix and not api_key.startswith(spec.key_prefix):
        raise LLMConfigurationError(
            f"{provider_id} expects keys to start with {spec.key_prefix!r}"
        )
    ...
```

Fails faster, doesn't consume a vendor request, doesn't echo the key.

### ⚠️ `httpx.HTTPError` mapped to generic `LLMError("transport error")` (P3)

Correct for key safety, but loses the distinction between DNS failure and TLS failure — both produce identical user-visible errors.

🔧 **How to Improve:** add `LLMTransportError` subtree:

```python
class LLMTransportError(LLMError):
    """A transport-layer failure (DNS, TLS, connection refused, socket reset).
    Distinct from LLMTimeoutError (which is also transport-layer but time-bound)
    and from LLMResponseError (which is application-layer)."""
```

Still no request material in the message. Slightly better debugging signal.

### ⚠️ No in-process rate-limit / spend-cap budget (P2)

For a shared seam where one consumer's runaway loop is a portfolio-wide problem, an in-process budget primitive is worth at least sketching.

🔧 **How to Improve:** sketch a `Budget` Protocol:

```python
class Budget(Protocol):
    def allow(self, estimated_tokens: int) -> bool: ...
    def record(self, actual_input: int, actual_output: int) -> None: ...
```

Threaded through `Provider.generate()` as optional. Reference implementation: `WindowedTokenBudget(max_tokens_per_min=100_000)`.

---

## 6. Distribution / Ops Practices

### ✅ Optional vendor SDK as extra

`anthropic` is in `[project.optional-dependencies] anthropic = [...]`. Consumers that only use OpenAI-compat providers don't pull it in. `anthropic_native.py` imports it lazily and raises `LLMConfigurationError` if absent.

### ✅ No state, no warm-up

A provider instance is created per request (BYOK) or pooled (managed). No global initialisation, no lazy module-level singletons. Right shape for serverless and per-worker FastAPI alike.

### ⚠️ License contradiction: `Proprietary` in pyproject vs `public` on GitHub (P1)

`pyproject.toml` says `license = { text = "Proprietary" }` but the GitHub repo is public. Either re-license to permit the use cases the public repo invites, or re-private with an internal distribution model.

🔧 **How to Improve:** make a decision and propagate it. Two clean options:

- **Stay public:** change to a permissive license (Apache-2.0 / MIT) consistent with the public-repo visibility. Add `LICENSE` file in the repo root.
- **Stay proprietary:** make the repo private; share access via the same `org-token` pattern as the `*-memory` repos. Add `LICENSE` file with the proprietary terms.

A public repo with a `Proprietary` license is the worst-of-both: legally ambiguous for external readers, friction-creating for any would-be contributor, and unhelpful to the consumer who pinned it via `git+https`.

### ⚠️ No PyPI release (P2)

Consumers pin to `git+https://github.com/wegofwd2020-hub/wegofwd-llm@v0.1.2`. Every CI run that doesn't cache the install pulls source from GitHub. Already-flagged in `mentible-critique.md` v2.0.

🔧 **How to Improve:** wire a release-on-tag workflow that publishes to a private package registry (GitHub Packages, AWS CodeArtifact, or a private PyPI):

```yaml
name: release
on:
  push:
    tags: ['v*']
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install build hatchling
      - run: python -m build
      - run: # publish dist/* to your chosen registry
```

Consumers pin `wegofwd-llm==0.1.2` instead of a git URL; CI installs are cached; Mentible's `v0.1.0` lag becomes a one-line bump.

### ⚠️ Gemma is dead-on-arrival in the registry (P0 — easy fix)

`ProviderSpec(base_url="")` for gemma means construction raises `LLMConfigurationError`. Loud failure, but a misleading registry row.

🔧 **How to Improve:** add an `available: bool` field to `ProviderSpec`, default `True`; have `available_providers()` filter on it; mark gemma `available=False` until wired:

```python
@dataclass(frozen=True)
class ProviderSpec:
    ...
    available: bool = True  # False = registered but not yet wired (visible in docs, hidden from picker)

# in registry
"gemma": ProviderSpec(
    provider_id="gemma",
    openai_compatible=True,
    base_url="",  # UNVERIFIED — depends on hosting
    default_model="gemma-2-27b-it",  # UNVERIFIED
    capabilities=Capabilities(json_object=False, max_context=8_000),
    managed_env_key="GEMMA_API_KEY",
    available=False,  # not yet wired; hidden from build_provider's allow-list
),
```

```python
def available_providers(allowed=None) -> list[str]:
    ids = [p for p, spec in PROVIDER_REGISTRY.items() if spec.available]
    ...
```

Then `build_provider("gemma", ...)` raises an explicit `LLMConfigurationError("gemma provider is registered but not yet available (base_url unset); see PROVIDER_REGISTRY")` instead of the misleading `requires a base_url` error.

---

## 7. Scorecard

```
┌──────────────────────────────────────────────────────────────────────┐
│  wegofwd-llm — Practice Scorecard (v1.0, 2026-06-13, HEAD 4823606)    │
├─────────────────────────────────────┬───────────────┬────────────────┤
│  Discipline                         │  Current      │  Note           │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Scope restraint (subtractive)      │  Excellent    │  9 things in,   │
│                                     │               │  ~6 deliberate  │
│                                     │               │  outs           │
│  Contract design                    │  Excellent    │  96-line single │
│                                     │               │  file; frozen   │
│                                     │               │  dataclasses    │
│  Provenance / versioning            │  Excellent    │  Three axes;    │
│                                     │               │  stamped        │
│  Type discipline                    │  Excellent    │  PEP 561; ruff  │
│                                     │               │  config mirrors │
│                                     │               │  consumers      │
│  Exception safety / key handling    │  Excellent    │  raise ... from │
│                                     │               │  None everywhere│
│  Test mocking discipline            │  Strong       │  Injected SDK;  │
│                                     │               │  MockTransport  │
│  Documentation                      │  Strong       │  Module         │
│                                     │               │  docstrings     │
│                                     │               │  carry the WHY  │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Key-leak regression coverage       │  Critical gap │  Zero tests on  │
│                                     │  (P1)         │  the load-bear- │
│                                     │               │  ing rule       │
│  Per-provider live-smoke CI         │  Needs adding │  Gemini lesson  │
│                                     │  (P1)         │  would have hit │
│  License / public-repo coherence    │  Contradiction│  Pick one and   │
│                                     │  (P1)         │  propagate      │
│  Provider verification matrix in    │  Hidden in    │  README table   │
│  README                             │  code (P1)    │  needed         │
│  In-package retry / failover policy │  Absent (P1)  │  Errors typed   │
│                                     │               │  for it; policy │
│                                     │               │  isn't there    │
│  Gemma registry entry               │  DOA (P0)     │  available=False│
│                                     │  easy fix     │  pattern        │
│  Observer / metrics hook            │  Absent (P2)  │  Each consumer  │
│                                     │               │  instruments    │
│                                     │               │  independently  │
│  PyPI / package-registry release    │  git+https    │  Consumer pin   │
│                                     │  only (P2)    │  lags already   │
│  CHANGELOG / SECURITY.md            │  Absent       │  Public-repo    │
│                                     │  (P1/P2)      │  hygiene        │
│  Sync-only documentation            │  Absent (P2)  │  Async consumers│
│                                     │               │  surprised      │
├─────────────────────────────────────┼───────────────┼────────────────┤
│  Overall library health             │  Strong + pre-│  Disciplined    │
│                                     │  1.0 polish   │  core; missing  │
│                                     │  needed       │  the regression │
│                                     │               │  guards         │
└─────────────────────────────────────┴───────────────┴────────────────┘
```

The headline: **the design discipline is excellent and the test discipline lags it**. The library does the hardest thing right (key safety, exception chaining, contract typing, capability gating) and the easiest thing not-yet (a single test that asserts the key-safety rule under the worst case). The fixes are short, mostly mechanical, and all listed in `wegofwd-llm-critique.md` §7.

---

*Companion files: [wegofwd-llm-critique.md](wegofwd-llm-critique.md) for the point-in-time code review, [wegofwd-llm-development-pattern.md](wegofwd-llm-development-pattern.md) for the scoping/timing/cadence analysis, [wegofwd-llm-cost.md](wegofwd-llm-cost.md) for the real-world cost analysis.*
