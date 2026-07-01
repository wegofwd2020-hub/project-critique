# wegofwd-video — Development Pattern

**Reviewed:** 2026-07-01 (v1.0 — first development-pattern analysis, companion to `wegofwd-video-critique.md`) · Reviewer: Claude (Anthropic)
**Repo:** `wegofwd2020-hub/wegofwd-video` · HEAD `233f248` (v1.0.0)
**Focus:** How this library was scoped, why it was built *up front* instead of extracted, what it inherited from `wegofwd-llm`, and what a two-and-a-half-hour build teaches about a maturing "shared-seam" muscle.

---

## 0. Why this lens matters

`wegofwd-video` is the third piece of pure **infrastructure** in the portfolio — a shared multi-provider seam, no user, no buyer, no audience — and the second one worth analyzing for its *development pattern* specifically. But it is not a repeat of `wegofwd-llm`. It is the interesting counter-case.

`wegofwd-llm` was **extracted** from a running app after that app had already proven the surface in-repo — the "extract-then-use" / "proven-in-repo-then-package" pattern, and the family's binding default (ADR-019: *copy-first, extract on the second real consumer*). `wegofwd-video` **inverts** that. It was created standalone, up front, before either intended consumer had a single line of running integration code — a move ADR-026 D7 records explicitly as a *conscious exception* to ADR-019 (`ADR-026:151-186`).

That inversion is the whole story. This file documents:

- The **scoping decision** — library, not service, and why the boundary sits where it does (§1).
- The **timing inversion** — up-front-build vs extract-later, why it was safe *here* and nowhere else, contrasted directly with `wegofwd-llm` (§2).
- The **boundary discipline** — caller owns secrets, state, storage; product schemas stay out (§3).
- The **cadence** — four commits in one evening, and a demand-driven patch bump that proves the validation loop was live (§4).
- The **inherited pattern** — this is *pattern* reuse of `wegofwd-llm`, not code reuse, and what that says about the meta-pattern (§5).
- The **interface-freeze gate** as a deliberate risk-management device (§6).
- What still has to prove out before the payoff is real (§7).

---

## 1. Scoping — a library, not a service, and where the boundary sits

The rejected alternative is a central video-generation *service* both apps call. ADR-026 D1 (`ADR-026:78-96`) kills it on the same grounds ADR-012 killed a central LLM service — no new 24/7 infra, no key honeypot, no single failure point — **plus** one grounds specific to this seam: a central service would route kathai-chithiram's pseudonymized-but-sensitive child content through code kathai does not control, defeating its dispatch-time no-training / zero-retention guarantees (`ADR-026:89`). The privacy row is decisive; the library keeps generation inside the process that owns both the data and the key.

Video differs from the text seam in three ways that *sharpen* the boundary without changing the library-vs-service answer (`ADR-026:60-72`): generations are long-running (minutes, so submit→poll, not request→response), outputs are MB-scale binaries needing object storage, and each call is expensive enough to make generate-and-select a deliberate workflow. Every one of those differences is pushed back across the boundary to the caller:

| Concern | In `wegofwd-video`? | Where it lives instead |
|---|---|---|
| Provider registry, roles, capability checks | ✅ `registry.py` | — |
| Brief → vendor-request shaping | ✅ `contract.py` / providers | — |
| Provenance stamping | ✅ `contract.py:149-164` | — |
| Typed error hierarchy | ✅ `errors.py:13-46` | — |
| Sync `generate()` (submit→poll→download) | ✅ `providers/veo.py:119-158` | — |
| **Queue / async orchestration** | ❌ Out (D2) | Pramana=Celery, kathai=subprocess |
| **Storage of the MB-scale artifact** | ❌ Out (D2) | Caller: S3 key on `CourseVersion.video_asset_id`, or `media/<file>` on disk |
| **Secret sourcing** | ❌ Out (D2, BYOK) | Caller passes `api_key=`; package never reads `os.environ` |
| **The heavy render code** (blender/matplotlib) | ❌ Out (D4) | Stays in kathai; injected as a callable |
| **Product `StoryUnit` schema, governance, prompts** | ❌ Out (D3) | Stays in `project-critique/story-video-template/` |

This is the same *subtractive* scoping as `wegofwd-llm`: the library names every concern it will not own and hands it back. The `VideoResult` even carries `asset_bytes` and `asset_uri` as two `field(..., repr=False)` slots (`contract.py:91-105`) — it *returns* the bytes but refuses to *persist* them. That is the boundary in a single dataclass: the package produces the artifact, the caller decides where it lives.

---

## 2. Timing — the inversion, and why it was safe here

### 2.1 The default this breaks

`wegofwd-llm`'s extraction happened at a precise, correct moment: a second consumer (StudyBuddy_OnDemand) was actively re-implementing the surface, so the seam was pulled out *with a typed contract* and re-injected into both consumers in the same window. That is extract-then-use, and it is the family default (ADR-019).

`wegofwd-video` has **zero running consumers of the AI seam** at creation time — Pramana has no video generation, kathai only has its local renderer (`ADR-026:154-158`). By the default, the correct move would be to build the seam in one app first and extract later. ADR-026 D7 deliberately does the opposite and creates the standalone package *now*.

```
The two timing shapes, side by side

  wegofwd-llm (extract-then-use)          wegofwd-video (validate-then-build)
  ┌───────────────────────────────┐       ┌────────────────────────────────────┐
  │ Build in-repo for consumer #1  │       │ Design the contract on paper        │
  │ Prove the surface in Mentible  │       │ Validate against BOTH consumers as  │
  │ Consumer #2 arrives, live PRs  │       │   two worked examples (kathai +     │
  │ EXTRACT with a typed contract  │       │   pramana) BEFORE any package code  │
  │ Re-inject into both same week  │       │ BUILD the package standalone first  │
  │ One copy, two consumers        │       │ Wire both REAL integrations after   │
  └───────────────────────────────┘       │ FREEZE at v1.0 once both are green  │
   Proven in code, then packaged           └────────────────────────────────────┘
                                            Proven on paper, then built, then frozen
```

### 2.2 Why the inversion was safe *here*

The risk ADR-019 guards against is *freezing guesses* — abstracting an interface before any real caller has shaped it. D7's justification is that the guesses were already checked (`ADR-026:160-173`):

1. **The interface had met both consumers concretely, not just in principle.** The seam was fully specified and validated as *two worked examples* — `example.kathai.json` and `example.pramana.json` in `project-critique/story-video-template/` — proving one contract fits both a special-needs-animation domain and a corporate-compliance-lesson domain *before* a package file existed. Unlike ADR-019's identity case (one *Proposed* design, zero implementations), the premature-abstraction risk was materially lower because the guesses had been checked against both callers.
2. **Both consumers were known and committed, not hypothetical.**
3. **Adoption was intended to proceed in parallel**, so building in one app first would have created immediate two-way drift to reconcile; a single source from day one avoids it.

The `wegofwd_video.py` in the template is now a **breadcrumb** — its docstring reads *"PROMOTED. This sketch is no longer the source of truth"* and points at the real package, precisely to stop the cross-repo drift the ADRs warn against. The sketch was the validation artifact; once the package existed, the sketch was demoted to a pointer rather than left to fork.

### 2.3 The risk was capped, not waved away

ADR-026 is honest that this is *"a cross-repo interface frozen before two running callers exist"* (`ADR-026:222-226`) and accepts it explicitly. The two mitigations are the load-bearing part:

- **Ship v0.x (unstable) first**, additive-by-default, `VIDEO_CONTRACT_VERSION` starting at 1 (`contract.py:23`).
- **Treat the first two real integrations as the interface-freezing gate — v1.0 is not cut until both are wired and green** (`ADR-026:180-183`).

And critically, the exception is *scoped*: `ADR-026:185-186` states it does not relax ADR-019 for any other candidate — `wegofwd-billing` and the rest keep extract-on-second-consumer. That sentence is what keeps this from becoming a license to over-package the whole portfolio. The inversion is a one-off with a named justification, not a new default.

---

## 3. Boundary discipline — three seams held under pressure

### 3.1 The package never sources a secret (D2)

BYOK is enforced in code, not just documented. The Veo provider raises on an empty key (`providers/veo.py:80-81`), stores it privately, and passes it straight to the vendor client (`genai.Client(api_key=self._api_key)`); there is no `os.environ` read anywhere in the package. The README states the rule as a design fact: *"the caller passes the `api_key` string (BYOK)"* and *"never lets a key reach an exception, log line, `raw` field, or `repr`"* (`README.md:21-28`). The key-safety half of that is real: SDK exceptions are re-raised with `raise self._map_error(exc) from None` (`providers/veo.py:145`), and `_map_error` classifies on HTTP status code, never the exception string (`providers/veo.py:189-207`). This is the same `from None` discipline `wegofwd-llm` uses to keep a stringified request — key and all — out of a logged traceback.

### 3.2 The package returns the artifact but never stores it (D2)

`generate()` submits, polls in the caller's process, downloads the bytes, and returns a `VideoResult` (`providers/veo.py:119-158`). Where those bytes go — an S3 key stamped onto an immutable `CourseVersion` at publish, or a file under `media/` — is entirely the caller's. The library has no storage primitive to misconfigure.

### 3.3 The product schema stays out (D3)

The package owns the registry, brief-shaping, provenance, and capability checks and *nothing* about any app's data model (`ADR-026:110-116`). The `StoryUnit` JSON Schema, the Veo brief template, and the governance/privacy blocks all stay in `project-critique/story-video-template/`. There is no place in the package where a future product's schema would have to be added — which is exactly what makes the seam *shared* rather than *aligned*, the same test `wegofwd-llm` passes with its schema-agnostic validator callable.

### 3.4 The deterministic-renderer as a callable-injection seam (D4)

This is the most instructive boundary decision. kathai must keep its blender/matplotlib render path (for the child-safety reason in §1) while reusing the same brief, registry, and provenance vocabulary. The package solves this by defining the *interface* and wrapping a **caller-supplied render callable** (`providers/local_render.py:25-48`): `CallableRenderProvider` takes a `render_fn: Callable[[VideoRequest], VideoResult]` in its constructor and its `generate()` simply delegates (`result = self._render_fn(req)`). The heavy, product-specific, safety-critical code stays in kathai; only the seam lives in the shared package. `build_provider` exposes this by accepting `render_fn=` alongside `api_key=` (`registry.py:188-231`).

This is a deliberate "keep the heavy code in the consumer" pattern — the mirror image of BYOK. BYOK says *the caller owns the secret*; callable-injection says *the caller owns the implementation*, and the package owns only the shape that makes both providers substitutable through one registry. That two consumers on **two different provider paths** (Veo-AI vs deterministic-render) confirm the same registry/capability/provenance shape holds (`ADR-026:16-21`) is the strongest evidence the boundary was drawn in the right place.

---

## 4. Cadence — four commits in one evening

The entire library — scaffold, contract, registry, four providers, 30 tests, live Veo wiring, and a v1.0 release — was built in **one sitting of about two and a half hours** on the evening of 2026-06-30:

| Commit | Time (EDT) | Subject | Significance |
|---|---|---|---|
| `c73869f` | 17:21 | feat: scaffold wegofwd-video — shared video-generation seam (ADR-026) | v0.1.0 — the whole library in one go: contract, registry, both real providers, two placeholders, 30 tests |
| `75c2f0a` | 19:04 | chore: lower requires-python to >=3.10 for the kathai consumer (v0.1.1) | **Demand-driven** patch — the real consumer forced a change |
| `c69138a` | 19:35 | feat(veo): wire the live Veo generation call (v0.1.2) | Placeholder → live submit/poll/download call |
| `233f248` | 19:55 | release: v1.0.0 — freeze the interface (ADR-026 D7 gate met) | Both real integrations wired and green → freeze |

Three things stand out.

**The first commit was complete.** v0.1.0 already shipped 748 lines of production code across seven modules, 366 lines of tests, 30 tests, the full four-provider registry, provenance, and typed errors (`c73869f`, +1104 lines in one commit). Same signature as `wegofwd-llm`: when a thing is ready to exist, it ships as a useful whole, not a skeleton to be filled in later.

**The v0.1.1 bump proves the validation loop was live.** The requires-python floor was lowered to `>=3.10` (`pyproject.toml:14`, comment at `pyproject.toml:10-13`) because **kathai is a 3.10 consumer and pramana is 3.12**. This is exactly the class of late discovery D7 named as the cost of building ahead of the rule (`ADR-026:22-23`) — and it landed as expected. The patch is small (`pyproject.toml`, 2 lines to the version), but it is the receipt that "validate against real consumers" was not a slogan: a real consumer's Python floor reached back into the package within the same evening.

**The interface was only frozen after both integrations were green.** v0.1.2 wired the live Veo call, and only then was v1.0 cut — the D7 gate, met (`ADR-026:26-29`). The version numbers are the risk ledger: three patch releases at v0.x while the shape could still move, one minor-to-major jump the moment it could not.

---

## 5. Inherited pattern — reuse of `wegofwd-llm`, by type not by copy

`wegofwd-video` reuses `wegofwd-llm`'s pattern almost verbatim, and it is worth being precise that this is *pattern* reuse, not code extraction. Nothing was copied out of `wegofwd-llm`; the second library independently re-instantiates the same shape:

| `wegofwd-llm` element | `wegofwd-video` counterpart |
|---|---|
| `ProviderSpec` dataclass | `VideoProviderSpec` (`registry.py:34-43`) — `provider_id`, `default_model`, `capabilities`, `model_verified`, `integration_version`, mirrored field-for-field |
| `ROLE_DEFAULTS` role→(provider,model) | `ROLE_DEFAULTS` (`registry.py:109-113`) — `narrative-video`→`(veo, veo-3.1)`, `safety-render`→`(deterministic-renderer, …)` |
| `build_provider(...)` with allowlist-before-construction | `build_provider(...)` (`registry.py:188-231`) → `validate_selection` checks unknown-then-allowlist *before* any provider object is built (`registry.py:127-138`) |
| Typed error hierarchy, `from None` key-safety | `VideoError` + subclasses (`errors.py:13-46`); `from None` at `providers/veo.py:145` |
| `provenance()` stamp, three-axis versioning | `provenance()` (`contract.py:149-164`) stamps `contract_version`, `integration_version`, `model_verified`, `seed` — the same cross-product vocabulary |
| UNVERIFIED-placeholder honesty convention | `runway`, `kling` carried as `model_verified=False` placeholders (`registry.py:82-104`); `veo` and `deterministic-renderer` marked `True` (`registry.py:63,80`) |
| Ruff config `E W F I B C4 UP S T20 RUF` | Identical select set (`pyproject.toml:40`), with the comment that it *"mirrors wegofwd-llm so a file passes lint identically across the family"* (`pyproject.toml:34`) |
| Optional vendor dep, zero core deps | `dependencies = []` (`pyproject.toml:22`); `[veo]` extra pulls `google-genai` only (`pyproject.toml:25`) |

The provenance stamp deserves a note — and it exposes the one place where the pattern's discipline slipped. The *intent* (`registry.py:8-12`, README, `ADR-026:143-150`) is that `model_verified` stays `False` for Veo until a first real generation succeeds — the same honesty convention the LLM registry uses for an unrun provider. But the code actually ships `model_verified=True` for `veo` (`registry.py:63`), so `provenance()` stamps a live-verified basis onto an integration that has never returned a real byte. The convention is right; the value contradicts it. This is carried as a headline finding in the [critique](wegofwd-video-critique.md) (§6) — worth calling out here because it's a pattern-fidelity lapse, not just a bug: the whole point of provenance-as-shared-vocabulary (D6) is that the flag is trustworthy.

This is the *second* application of a meta-pattern, and that is the real inheritance. `wegofwd-llm` was the first product of "extract a seam, standardize it as a `wegofwd-*` package." `wegofwd-video` is the first time that *standardization template* was applied without an extraction underneath it — the shape was portable enough to instantiate from a paper contract. ADR-026 even flags the cost: if `registry` / `provenance` / `errors` keep duplicating across the two libraries, a tiny `wegofwd-core` may be warranted — deferred for now, because ADR-019 warns against extracting shared scaffolding pre-need (`ADR-026:209-211`). The portfolio is watching its own duplication and choosing, correctly, not to extract the meta-seam until a third instance justifies it.

---

## 6. The interface-freeze gate as a risk-management device

The single most transferable idea in this build is the **v1.0-only-when-both-consumers-are-green gate**. It converts the ADR-019 risk — a cross-repo interface frozen too early — from a hope into a mechanical condition. The package was allowed to say almost anything while it was v0.x; it was allowed to say something *permanent* only after two real callers on two different provider paths had exercised it. The gate is what makes the up-front build defensible: the inversion of the extract-later default is paired with a stricter-than-usual freeze discipline, so the net risk is bounded.

Two anti-patterns the gate (and the surrounding scope discipline) avoided:

- **A premature v1.0.** Freezing at scaffold time would have locked in guesses. The requires-python discovery (§4) alone would have forced a contract-adjacent churn under a "stable" banner. Staying at v0.x until the gate absorbed that discovery quietly.
- **A batteries-included service.** Every heavy concern that a "helpful" video library could have grown — the queue, the storage adapter, the render engine, the secret store — is exactly the thing that would have coupled it to *one* consumer's policy and broken the other's (kathai's privacy, most sharply). The deterministic-renderer callable-injection is the clearest refusal: the library could have shipped a matplotlib renderer; instead it ships an empty seam and lets kathai keep its own.

Honestly noted: the gate also *deferred* a real feature. Veo's Ingredients-to-Video (reference-image) wiring is not implemented — `generate()` raises `VideoConfigurationError` if a brief carries ingredients (`providers/veo.py:122-127`), and a test pins that this is intentional: `test_veo_generate_rejects_ingredients_until_wired` asserts the rejection (`tests/test_providers.py:164-168`). That is the right way to defer: the not-yet-wired boundary is asserted by a test, so it cannot be silently "finished" without the test noticing.

---

## 7. What this teaches the portfolio — and where the payoff is still pending

The maturing muscle this build demonstrates is **the shared-seam-from-a-validated-contract**: the portfolio can now, in a single sitting, stand up a new `wegofwd-*` library by re-instantiating the LLM template against a contract that has already been proven on paper against every intended consumer. That is a real capability — the first library took a multi-week extraction; the second took an evening — and it is *disciplined*, because the up-front build is fenced by the v0.x-then-freeze gate and explicitly forbidden from becoming the new default (`ADR-026:185-186`).

But the payoff is not yet fully realized, and the document should say so plainly:

- **The live Veo path is unproven.** The submit/poll/download call is wired (`providers/veo.py:119-158`), but Veo has never been live-tested from this stack — the remaining open item in the ADR (`ADR-026:26-29`, `ADR-026:204-205`) — even though the registry already flags it `model_verified=True` (the fidelity lapse noted above). A v1.0 with a frozen interface still rests on a vendor call that has not returned a real byte.
- **Two of four providers are placeholders.** `runway` and `kling` are honest UNVERIFIED stubs (`registry.py:82-104`). The registry's honesty is a strength, but the "multi-provider" promise is, today, two working providers and two names.
- **A feature is deferred, by design but still deferred.** Ingredients-to-Video — the mechanism the brief template leans on for cross-shot consistency — is stubbed out (`providers/veo.py:122-127`).
- **The dedup-vs-`wegofwd-llm` question is open.** The registry/provenance/errors scaffolding is now duplicated across two libraries; `wegofwd-core` is flagged and deferred (`ADR-026:209-211`). The right call for now, but an unresolved one.
- **No in-repo CI or watch.** There is no `.github/workflows` and no pre-commit config in the package. The lint-parity claim (`pyproject.toml:34`) is real but unenforced by automation; the 30 tests run only when someone runs them.

The thesis, then, is a qualified success. `wegofwd-video` shows the portfolio can invert its own extract-later rule *safely* when — and only when — the contract has already been validated against every real consumer and the freeze is gated on those consumers going green. It is the discipline around the exception, not the exception itself, that is the transferable lesson. The library exists and is frozen; whether the inversion truly paid off waits on a live Veo generation and a second real provider proving the seam under load.

---

*Companion files: [wegofwd-video-critique.md](wegofwd-video-critique.md) for the point-in-time code review · [wegofwd-video-practices.md](wegofwd-video-practices.md) for the good/bad catalogue · [wegofwd-video-cost.md](wegofwd-video-cost.md) for the real-world cost analysis.*
