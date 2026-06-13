# wegofwd-llm — Development Pattern

**Reviewed:** 2026-06-13 (v1.0 — first development-pattern analysis, companion to `wegofwd-llm-critique.md`)
**Repo:** `wegofwd2020-hub/wegofwd-llm` · HEAD `4823606` (v0.1.2)
**Focus:** How this small library was scoped, why it was extracted *when* it was, what design choices it inherited from its parents, and what the development cadence teaches.

---

## 0. Why this lens matters

`wegofwd-llm` is the only repository in the v2.6 portfolio that is **infrastructure rather than a product**. Looking at *how* it was scoped is different from looking at how a product was scoped — there is no user, no buyer, no compliance framework, no audience. The decision-making texture is purely architectural. That makes it a useful lens on the rest of the portfolio: the rules that emerged here are visible in the products too, but easier to read because the library is small.

This file documents:
- The **scoping decision** — what is in the seam and what is deliberately left out (§1).
- The **timing decision** — why the extraction happened *when* it did, not earlier or later (§2).
- The **design choices** — three rules that shape every file (§3).
- The **cadence** — what three commits and two patch versions reveal about the pace and the discipline (§4).
- The **inherited patterns** — what carried over from StudyBuddy_SelfLearner and from the org-wide coding standards (§5).
- The **anti-patterns avoided** — what a less disciplined extraction would have shipped (§6).

---

## 1. Scoping — what is in the seam, what is deliberately out

A multi-provider LLM seam *could* include all of the following:

| Candidate concern | In `wegofwd-llm`? |
|---|---|
| Typed provider-agnostic request/response | ✅ Yes (`contract.py`) |
| Registry of providers with capability flags | ✅ Yes (`registry.py`) |
| Logical-role pinning (authoring / toc / fast-draft) | ✅ Yes (`ROLE_DEFAULTS`) |
| Schema-agnostic validate→repair loop | ✅ Yes (`conformance.py`) |
| Typed error hierarchy with key-leak prevention | ✅ Yes (`errors.py`) |
| Anthropic native provider (tool-use JSON path) | ✅ Yes (`anthropic_native.py`) |
| OpenAI-compatible providers (one client, many vendors) | ✅ Yes (`openai_compatible.py`) |
| Three-axis versioning + provenance stamping | ✅ Yes (`LLM_CONTRACT_VERSION` + `provenance()`) |
| Retry policy / exponential backoff | ❌ **Out** — typed as "Retryable / failover candidate" in errors; policy belongs to callers |
| Failover / circuit-breaker | ❌ **Out** — same reason |
| Token-usage metering / spend cap | ❌ **Out** — `LLMResponse` reports `input_tokens` / `output_tokens` but no budget primitive |
| Async API (`AsyncProvider`) | ❌ **Out** — sync only; async consumers must wrap |
| Vendor SDK as required dep | ❌ **Out** — `anthropic` is an optional extra; OpenAI-compat speaks raw HTTP |
| Secret sourcing (env, Vault, keyring) | ❌ **Out** — caller always passes `api_key=` |
| Observer / metrics hook | ❌ **Out** — no plug-in surface yet |

The pattern in the right column is *subtractive*: the library names every concern it is **not** going to own, and pushes it back to the caller. The README states this explicitly — *"Library, not a service. Each consumer pip installs this and runs it in-process, making its own vendor call with its own key — there is no `wegofwd-llm` server."*

**Why subtract?** Because the alternative — a "batteries-included" SDK that does retries, failover, metering, and key management — would couple the library to *one* policy choice. StudyBuddy_OnDemand's policy (Celery + per-pipeline-job spend cap) is not Mentible's policy (in-process `BackgroundTask` + per-job HKDF envelope) is not Kathai Chithiram's policy (one-shot synchronous render). Each consumer's needs are different; the seam stays useful only by staying narrow.

This is the same shape as the StudyBuddy *three-runtime-context* boundary (pipeline / backend / client) and as Thittam's *vertical plugin system* (one core, many configurations). It is the founder's repeating pattern: **separate the surface from the policy**.

---

## 2. Timing — why extract *now* and not earlier or later

The extraction happened at a precise moment, recorded in commit `16bb0eb`:

> `feat: extract the multi-provider LLM seam from StudyBuddy_SelfLearner`

Read against the StudyBuddy_OnDemand timeline: PRs `eddf4c9` ("feat(llm): back anthropic+openai with the shared wegofwd-llm package (ADR-012)") and `36196b8` ("feat(llm): migrate google onto wegofwd-llm's gemini — finish ADR-012 consolidation") landed in the *same window*. The extraction was not speculative DRY — it was driven by an actual incoming second consumer.

The architect's well-known anti-pattern here is **extracting too early**: pulling shared code into a library "in case it's needed later," forking the development of the original product, and shipping the library against requirements that turn out not to match what the eventual second consumer needs. The cure for this is *Rule of Three* (wait for the third consumer before extracting). But Rule of Three has its own failure mode: by the time the third consumer exists, the second has already re-implemented the surface, and the cleanup cost is the same as Rule of Two would have been.

This extraction split the difference correctly:

```
The Extract-Then-Use Timing Decision

  Too early:                       Too late:                       This:
  ┌────────────────────────────┐   ┌────────────────────────────┐   ┌─────────────────────────────┐
  │ Build it for consumer #1   │   │ Build it for consumer #1   │   │ Build it for consumer #1     │
  │ Speculate consumer #2      │   │ Build it for consumer #2   │   │ Recognize consumer #2 coming │
  │ Extract, hope to be right  │   │   (duplicate)              │   │ Extract WITH typed contract  │
  │ #2 arrives, doesn't fit    │   │ Realize the duplication    │   │ Re-inject into BOTH same week│
  │ Refactor library to match  │   │ Extract under pressure     │   │ Retire #1's call sites       │
  │ Or: maintain two forks     │   │ Carry a long deprecation   │   │ One copy, two consumers      │
  └────────────────────────────┘   └────────────────────────────┘   └─────────────────────────────┘

  The discriminator: consumer #2 must be REAL and ACTIVE,
  not anticipated. Here, #2 was a live PR sequence, not a roadmap item.
```

The cost of getting this wrong twice in the same portfolio would have been compounding: every consumer that re-implemented the seam locally would have made its own choices about JSON-mode handling, error mapping, and key safety — none of them informed by the others' incidents. The extraction at this moment locks the lessons in place across the family before they can diverge.

---

## 3. Three design choices that shape every file

### 3.1 The package never sources keys

Every constructor takes `api_key=` as a required argument. There is no `os.environ.get("ANTHROPIC_API_KEY")` anywhere in the package. The decision is documented in the README as one of "two rules that make it reusable" — and enforced in code:

```python
if not api_key:
    raise LLMConfigurationError("anthropic provider requires a non-empty api_key (BYOK)")
```

The architectural payoff is that **the caller owns the secret-handling policy**. Mentible holds the key in memory after a per-job HKDF envelope decrypt; OnDemand reads it from a backend env var (Pattern A); a future managed path could pull from Vault. The library is neutral to all of these; it just refuses to invent one.

This is the same discipline as Thittam's secret tiering (T1 = Vault → memory; T2/T3 = env; T4 = config) and StudyBuddy's three-context boundary (only the pipeline ever sees the Anthropic key). The library inherits the discipline; it doesn't redefine it.

### 3.2 No exception ever carries a key string

Every SDK / HTTP exception path uses `raise LLMError(...) from None` — never `from exc`. The `from None` is the load-bearing word: it explicitly breaks the exception chain so that an underlying SDK exception's `repr()` (which can stringify the request, including the api_key) cannot show up in a logger's `exc_info=True` output.

```python
try:
    message = self._client.messages.create(**kwargs)
except Exception:
    # Never chain — SDK exceptions may include the api_key in their repr.
    raise LLMError("anthropic call failed") from None
```

This is the kind of rule that looks paranoid until you have seen an incident report where a 5xx exception page on a staging environment included `Authorization: Bearer sk-ant-...` in the rendered traceback. The library's hard rule prevents the class.

### 3.3 The contract is schema-agnostic

`generate_validated` takes a caller-supplied `validate(text) -> parsed` callable that raises on invalid output:

```python
result = generate_validated(
    provider,
    LLMRequest(prompt=prompt, response_format="json"),
    validate=my_schema_check,   # raises on invalid; returns parsed on success
)
```

The library carries **no** product schema. Lessons (StudyBuddy_OnDemand), authoring units (Mentible), compliance docs (Pramana-future), scene scripts (Kathai Chithiram) all reuse the same conformance loop with different validators. This is what makes the seam genuinely *shared* rather than *aligned*: there is no place in the library where a future product's schema would have to go.

The contrast is with most LLM "wrapper" libraries, which ship a `BaseModel`-style integration with one schema library (Pydantic, usually) and inadvertently couple every consumer to that choice. The wegofwd-llm choice is the right one for a portfolio with five different schema needs.

---

## 4. Cadence — what three commits in five days teach

| Commit | Date | Subject | Significance |
|---|---|---|---|
| `16bb0eb` | 2026-06-04 | feat: extract the multi-provider LLM seam from StudyBuddy_SelfLearner | v0.1.0 — initial extraction; the whole library shipped in one go |
| `5db7c02` | 2026-06-05 | fix(packaging): ship py.typed marker (PEP 561) → v0.1.1 | Caught at the *first* consumer install; fixed within a day |
| `4823606` | 2026-06-09 | fix(gemini): default to gemini-2.5-flash (verified live) → v0.1.2 | Caught during a live verification pass against the registered providers |

Three things stand out in this short trail:

**The first version was complete.** v0.1.0 already had the contract, the registry, both providers, the conformance loop, the typed errors, the tests, and the CI. There was no "ship the skeleton first, add modules later" pattern — the library shipped as a useful whole on day one. This is consistent with the founder's pattern across the portfolio: when a thing is ready enough to extract, it ships ready.

**v0.1.1 was caught by a downstream installer, not a unit test.** PEP 561 type-checking only matters once a consumer runs `mypy` against the installed package. The first consumer install surfaced the missing marker; the fix was a one-line packaging change. The lesson is that some classes of bug *cannot* be caught upstream — they require a real consumer install. The library's response was to fix it within a day rather than rationalize it.

**v0.1.2 was caught by a live verification, not a fixture.** Gemini's 2.0-flash hit free-tier quota; 1.5 was retired by Google. The fix moved the default to `gemini-2.5-flash` and stamped the verification date inline in the registry comment:

```python
default_model="gemini-2.5-flash",
# Conservative output cap (2.5-flash supports up to 65536) to stay clear of
# free-tier per-request/TPM limits that reject over-budget requests.
```

The lesson here is **the verification trail belongs in the code, not in a separate doc**. The registry entry doubles as the "I checked this on this date" log. Future regressions will have a specific date to compare against.

The development pattern: **three commits, three classes of bug, three fixes within the same week**. The cadence is the discipline.

---

## 5. Inherited patterns

`wegofwd-llm` did not invent its rules — it inherited them from two upstreams. Naming them clarifies what is portable and what is project-specific.

### 5.1 From the org-wide `coding-standards` repo

| Standard | Where it shows up in `wegofwd-llm` |
|---|---|
| Rule: secrets tiered by classification, T1 in memory only | `if not api_key: raise...` + `raise ... from None` everywhere |
| Rule: monetary precision (never float) | N/A here — no money — but the same instinct: `int` for token counts, `Decimal`-style discipline |
| Rule: every write safe to retry | Reflected as the conformance loop's *retry the validator failure, not the network call* design |
| Rule: typed errors, not string-matched | `LLMError` hierarchy lets callers route on type, never on message text |
| Ruff config: `E W F I B C4 UP S T20 RUF` | Same config in `wegofwd-llm/pyproject.toml` as in StudyBuddy + SelfLearner — a file passes lint identically here and in any consumer |

### 5.2 From StudyBuddy_SelfLearner (the parent)

| Pattern | Carried over |
|---|---|
| ADR-driven decisions | The library cites **ADR-012** for its rationale; the README links back |
| `LLM_CONTRACT_VERSION` stamped into provenance | Originally a SelfLearner concern (per-book pinning); now portfolio-wide |
| Capability-flag-driven request shaping | The `Capabilities` dataclass and its uses in `_response_format()` |
| `tokens_estimated` honesty flag | Says "the count is a fallback, not provider-reported" — borrowed from SelfLearner's token-metering work |
| Per-provider free-tier quirks documented inline | The Groq 413 / Gemini 2.0-flash quota notes were SelfLearner findings, preserved verbatim in the registry |

The extraction was not just "move the files into a new repo." It was also a chance to *promote* SelfLearner's per-provider notes to first-class library documentation — they now apply to every consumer, not just the one that originally hit the wall.

---

## 6. Anti-patterns avoided

A less disciplined extraction would have shipped:

- **A class hierarchy.** `AbstractLLMProvider` → `BaseHTTPProvider` → `OpenAICompatibleBase` → `OpenAIProvider`. Tempting; almost always wrong. The library has *one* ABC (`Provider`) and two concrete classes (`AnthropicNativeProvider`, `OpenAICompatibleProvider`), with the OpenAI-compat one parameterised by `provider_id` + `base_url` + `capabilities`. Adding a vendor is a registry row + (if non-trivial) a constructor argument, not a subclass.

- **A vendor SDK as a hard dependency.** The `anthropic` SDK is in `[project.optional-dependencies] anthropic = [...]`. Consumers that only use OpenAI-compat providers (Groq, Gemini, OpenRouter, …) don't pull it in. `anthropic_native.py` imports it lazily and raises `LLMConfigurationError` if it's missing. This is the right shape: the rare consumer-with-Anthropic-only pays for one dep; the common consumer-with-many-providers gets one tight HTTP client.

- **A config file.** No YAML, no TOML beyond `pyproject.toml`, no `LLM_PROVIDERS.json`. The registry is a Python dict in source; adding a provider is editing one file in a normal PR review.

- **A `Provider.from_env()` factory.** Would have re-introduced the env-sourcing the BYOK rule explicitly forbids. The library refuses to provide it.

- **A `try: ... except Exception: pass`-style "be helpful" wrapper.** Every exception path either propagates a typed `LLMError` subclass or returns a normal `LLMResponse`. There is no place where a vendor error is silently swallowed.

- **An async-by-default API.** Would have forced every consumer to deal with async, including the synchronous Celery-task and one-shot-render consumers. Sync-first means callers who need async wrap with `run_in_executor` — at a cost of one line of glue per call site, which is the right trade for a v0.1.x library.

The pattern is **resist scope creep at extraction time**. Every "useful thing" the library could have grown would have made it less useful to one or more current consumers. The discipline of keeping it small is what kept it shared.

---

## 7. What this pattern teaches the rest of the portfolio

The `wegofwd-llm` extraction generalizes to a rule the portfolio can re-use:

> **Extract a shared library when, and only when, a second active consumer is about to re-implement the same surface — and extract with a typed contract, three-axis versioning, and re-injection of both consumers in the same cycle. Do not extract speculatively, and do not let the original copy drift.**

The same shape is visible (less crisply) in:

- **StudyBuddy's `pipeline/providers/` → `wegofwd-llm`** (the extraction itself).
- **Thittam's vertical plugin system** — extracted once two verticals were under construction; not earlier when only film production existed.
- **The `coding-standards` repo** — extracted into a separate repo only after the *third* project (Pramana) needed the same rules.

The discriminator everywhere is **the second consumer must be real**. The pattern that emerges from observing the portfolio over 18 months is: subtractive scope, late but uncoerced extraction, and a contract typed before any consumer gets to call it.

The architectural cost of getting this wrong is the same as the cost of getting it right plus one cycle of cleanup. The architectural benefit of getting it right is that the library, once shipped, gets to be useful immediately — not deprecated-because-it-was-the-wrong-shape, and not refactored-under-pressure later.

---

*Companion files: [wegofwd-llm-critique.md](wegofwd-llm-critique.md) for the point-in-time code review, [wegofwd-llm-practices.md](wegofwd-llm-practices.md) for the good/bad catalogue, [wegofwd-llm-cost.md](wegofwd-llm-cost.md) for the real-world cost analysis.*
