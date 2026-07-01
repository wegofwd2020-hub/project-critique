# Mentible — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle — from advisor feedback to a multi-provider, package-seam pre-deploy MVP
**Period:** 2026-04-25 → 2026-06-09 (~6.5 weeks, 228 commits)
**Last refresh:** 2026-06-09 (v2.0 — major refresh; measured on disk at `40166ee`, branch `main`. **97 commits since v1.0**; headline: the LLM provider seam was *extracted into the installable `wegofwd-llm` package* (ADR-012), intended to be shared across the product family (Mentible + Pramana, ADR-011/013) — a single-repo pattern designed to become a product-family pattern, though on disk Mentible is still its only consumer.)
**Prior refresh:** 2026-06-02 (v1.0 — first analysis, `e1c66f7`, branch `feat/authoring-regenerate-export-fixes`)
**Repo / brand:** `wegofwd2020-hub/Mentible` · public brand **Mentible** (*"Author Yourself"*)
**Related:** [mentible-critique.md](mentible-critique.md) · [mentible-practices.md](mentible-practices.md) · [mentible-cost.md](mentible-cost.md) · parent product: [studybuddy-development-pattern.md](studybuddy-development-pattern.md)
**Author:** WeGoFwd2020 / Claude (Anthropic)

> This is the development-method analysis: *how* the product was scoped, designed, and built — less about bugs (see the critique), more about the decision discipline. The defining trait remains that the project is **ADR-driven and spec-first to an unusual degree**. The v2.0 story is that the same discipline scaled from "re-scope one product with ADRs" to **"extract a shared seam across three products with ADRs"** — and that the one persistent weakness (promoting decisions back into the durable top-of-funnel spec) is still only half-fixed.

---

## What changed since v1.0 (the 97-commit window)

v1.0 analysed a single repo that had re-scoped itself twice in five weeks. v2.0 analyses the same repo after it (a) finished a re-scope it had only *decided* (multi-provider, ADR-005), (b) made a structural product-family move (extracting the provider seam into its own installable package, ADR-012), and (c) opened an inter-product integration (Mentible↔Pramana, ADR-011/013).

| Dimension | v1.0 (`e1c66f7`) | v2.0 (`40166ee`) |
|---|---|---|
| Commits (total) | 131 | **228** (+97) |
| ADRs | 6 | **13** |
| Provider layer | inlined per-provider, multi-provider *accepted but unbuilt* | **extracted to `wegofwd-llm` package, built, consumed by Mentible** (Pramana intended, not yet wired) |
| Product surface | Query single-lesson + books | **Books-only** (Query removed, ADR-009) |
| Inter-product integration | none | **Mentible↔Pramana consumable handoff** (ADR-011 *Proposed*, ADR-013 *Accepted*) |
| In-repo production LOC | ~10,992 | **~13,118** + a new 773-LOC external seam package |

The instructive new pattern: **a within-repo seam was graduated into a cross-repo package in anticipation of a second consumer.** In v1.0 the provider abstraction was an ADR with `.pyc` orphans. As Pramana's generation needs were *foreseen* (ADR-013), the team didn't plan to copy the provider code a third time (the OnDemand→Mentible vendoring pattern) — they **promoted it to a package** (ADR-012, explicitly "a library, not a service," D8). Worth being precise: on disk Pramana does **not** yet import the package (a grep across all three repos finds the seam only in Mentible). So this is a *forward-looking* DRY decision — package the seam *before* the second consumer materializes — which is slightly riskier than the textbook "extract once you have two consumers," but defensible here because the seam was first proven in-repo across five phases (see §5) and the second consumer is a named, decided product, not a hypothetical.

---

## 1. Origin — a product born from a GTM critique (unchanged)

Mentible still starts from a **go-to-market objection** to a sibling product (OnDemand). The subtractive-scoping origin — "what is the smallest surface that preserves the moat and discards the cost?" — is documented in v1.0 and is unchanged. `SCOPE.md §8`'s "carried over / NOT carried over" ledger is still the design. What v2.0 adds is a *second* subtraction at the product surface: ADR-009 **removed** the Query single-lesson screen entirely once books became the product, narrowing rather than accreting.

---

## 2. The scoping artifact — a decision register that kept growing

`SCOPE.md` remains a decision register (D1–D19), and the ADR series is now the *living* register — it grew from 6 to **13** decision artifacts. Several D-decisions have been amended *in place by ADR*: D13/D16 are annotated "*(amended/superseded — ADR-009)*," D17 "*(amended — ADR-004)*." This is the pattern working: the spec's locked decisions are not deleted, they are **annotated with the ADR that revised them**, so the audit trail survives.

The weakness the pattern still carries: those annotations are *inline notes layered over a stale frame*. `CLAUDE.md`'s status header still says "Pre-MVP — directory stubs only, no application code yet" above a 13k-LOC codebase. The decisions are reconciled; the *framing* around them is not.

---

## 3. The defining pattern — ADR-driven re-scoping, now at product-family scale

| ADR | Status | What it changed |
|---|---|---|
| ADR-001 | Accepted (+amended) | BYOK Pattern B; **amended in this window to scrub the key from 422 responses** (a found leak class) |
| ADR-002 | Accepted | Vendoring (Approach C) — copy, don't import; record SHAs |
| ADR-003 | Accepted | Book authoring; local-first books |
| ADR-004 | Accepted | Two-product split; EPUB3 artifact; app becomes paid |
| ADR-005 | **Accepted → BUILT** | Multi-provider LLM + hybrid keys (was "unbuilt" in v1.0; now implemented across 5 phases) |
| ADR-006 | Accepted | Rebrand → Mentible |
| ADR-007 | Accepted (2026-06-03) | Book templates / theme system (content vs presentation) |
| ADR-008 | Accepted (2026-06-03) | Release lifecycle & watermarking (draft → release → editions) |
| ADR-009 | Accepted (2026-06-05) | **Books-only** — remove the Query single-lesson surface |
| ADR-010 | **Proposed** | Optional narrative + animated-character lesson mode (prototype code exists) |
| ADR-011 | **Proposed** | Mentible↔Pramana compliance integration (the consumable handoff) |
| ADR-012 | **Accepted (2026-06-09)** | **Shared LLM provider seam as an installable package** (`wegofwd-llm`) |
| ADR-013 | **Accepted (2026-06-09)** | **Pramana in-process generation** (amends ADR-011) — the artifact is the boundary, not the LLM call |

**The two most instructive new ADRs are 012 and 013, read together.** They resolve a real architectural tension *on paper*: if both Mentible *and* Pramana will need to call LLMs, where does the provider code live, and where is the line between the two products? ADR-012 answers the first ("a package, not a third copy; a library, not a service"). ADR-013 answers the second ("the **artifact** is the boundary — Pramana may call an LLM in-process to *draft* a clause-grounded quiz; Mentible owns the *authored consumable*; the LLM call itself is not the dividing line"). The losing option (Pramana defers *all* generation to Mentible) is closed in writing. This is the v1.0 pattern — "close the losers explicitly" — applied to an *inter-product* boundary. The honest caveat: both ADRs are decided ahead of Pramana's code, which on disk is only a thin outbound HTTP port (`mentible_client.py`, default `NullMentibleClient`).

**The risk this pattern now creates** is larger than v1.0's doc-drift: it is **cross-repo version coupling**, already visible with a single consumer. The package is at `v0.1.1` (a `py.typed` fix); Mentible still pins `wegofwd-llm@v0.1.0`. A consumer lagging its own dependency by a tag — before a second consumer even exists to disagree with — is ADR-velocity outrunning *version-reconciliation*, the same shape of gap as v1.0's ADR-outran-spec, one layer up the stack. It will compound the moment Pramana wires the seam.

---

## 4. Architecture method — security-first, isolation by process, now seam-by-package

The v1.0 method choices (threat-model-before-feature; isolate by runtime; vendor-don't-fork) all hold. v2.0 adds two:

**4.1 Make the security invariant a test even for a *newly discovered* leak.** The 422 key-echo leak was not in v1.0's threat model — the default FastAPI 422 handler echoes the request body, which on a missing-field error *is* the api_key. The team found it, closed it with a custom handler + `scrub_validation_errors`, and — crucially — **wrote `test_missing_field_422_does_not_echo_key` to lock it**. The method ("the invariant is a test, not a hope") extended to a regression class no one had predicted. That is the method proving itself under a new failure.

**4.2 Graduate a seam to a package, with a typed contract first.** `wegofwd-llm` was not extracted as a loose folder of helpers; it ships a typed `contract.py` (`LLMRequest`/`LLMResponse`/`Provider` ABC/`Capabilities`), a registry, and a conformance loop, with `py.typed` (v0.1.1) so consumers type-check against it. The package's `pyproject.toml` even **mirrors the consumers' ruff config** so a file lints identically in either repo. Extracting a seam *with its contract and its lint rules* — rather than just lifting code — is the disciplined version of this move.

**4.3 Per-provider capability modeling instead of one-size budgets.** The Groq HTTP-413 fix wasn't a hardcoded special-case; it added `Capabilities.max_output_tokens` to the contract and a `min()` clamp in the provider, so the *registry* declares each provider's ceiling. The fix generalized to a data-driven capability rather than an `if provider == "groq"`. Method signal: when a provider quirk appears, model the capability, don't branch on the name.

---

## 5. Build sequence — thinnest slice first, then a clean second-consumer trigger

The original sequence (BYOK loop → book authoring → rebrand) is intact. v2.0 adds the multi-provider and seam-extraction waves, and the ordering is legible in the commit log:

```
Loop 1 (ADR-001):            BYOK /generate + envelope + redaction + tests
Loop 2 (ADR-003/004):        TOC → book model → per-topic generate → EPUB3/PDF compiler
Loop 3 (ADR-006/007/008):    Mentible rebrand, templates/theme, release lifecycle
Loop 4 (ADR-009):            Books-only — remove the Query single-lesson surface
Loop 5 (ADR-005, 5 phases):  multi-provider seam in-repo → validate→repair → provider picker
                              → per-provider keystore → provenance → free providers → clamp fix
Loop 6 (ADR-012):            EXTRACT the seam to the wegofwd-llm package; consume it
Loop 7 (ADR-011/013):        Mentible↔Pramana boundary decided (HTTP handoff port; Pramana seam-use intended, not yet wired)
        (ADR-010):           narrative/animated mode — Proposed, prototyped
```

The clean signal in Loop 5→6: the seam was **built in-repo first, across five phases, and only extracted to a package once it was proven in production use.** The discipline that matters here is *proving the abstraction before packaging it* — the seam earned its package by surviving five phases of real multi-provider work (incl. the live Groq 413 clamp fix), not by being designed up front. The one place it deviates from textbook DRY is that the *second* consumer (Pramana) is anticipated rather than realized — so the package's reuse payoff is still a forecast.

---

## 6. What's deferred — and how honestly

The deferrals are still *named*. The in-process `BackgroundTask` still admits in its docstring that it stands in for Celery and loses jobs on restart. New honest markers in this window: provider paths tagged "**LIVE-UNVERIFIED**" / "unit-green" in commit messages (Anthropic tool-use), free-provider endpoints dated with a "verify + correct (2026-06-05)" pass, and several `# UNVERIFIED` default-model markers in the seam registry. The team labels what it has and hasn't confirmed against a live API — good discipline.

The execution gap is the same as v1.0, plus one: (a) the plan (`MVP_v1.md` "Celery") still contradicts the code (`BackgroundTask`); (b) the **version pin drift** (v0.1.0 vs v0.1.1) is a new "named-in-passing-but-not-reconciled" gap — the `requirements.txt` comment even tells you to prefer an editable install for local dev, acknowledging the multi-repo friction without resolving it.

---

## 7. Lessons this project teaches

1. **Scope subtractively — and keep subtracting.** v1.0's lesson was the "NOT carried over" ledger; v2.0 adds ADR-009 *removing* a shipped surface (Query) once the product clarified. Narrowing a live product is harder than not building it, and they did it cleanly.
2. **Vendor for one consumer; package when a second is committed.** The escalation from OnDemand→Mentible vendoring to a `wegofwd-llm` package is the DRY decision made *forward-looking* — packaged once the seam was proven in-repo and a second first-party consumer (Pramana) was a decided product, even though Pramana hasn't wired it yet. The honest version of the lesson: proving the abstraction in production *before* packaging is what de-risks a forward-looking extraction.
3. **Extract a seam with its contract, not just its code.** The package shipped a typed contract, a registry, conformance tests, `py.typed`, and a mirrored lint config — so consuming it is type-safe and lint-identical.
4. **Make even an unforeseen invariant a test.** The 422 key-echo leak was outside the original threat model; it became a custom handler *and* a locking test the day it was found.
5. **Model provider quirks as capabilities, not name-branches.** The Groq 413 fix added `max_output_tokens` to the contract and clamped via the registry — data, not `if`.
6. **A shared package moves the doc-drift risk up a level — to versions.** The one persistent weakness (promote decisions into the durable frame) now also means *keep the version pin current*. Mentible@v0.1.0 lagging the package's @v0.1.1 — with only one consumer so far — is v1.0's spec-lag failure mode, re-expressed as a dependency pin, and it will compound once Pramana becomes a second consumer.

---

*This analysis is drawn from the code on disk at `40166ee` (branch `main`), the 13 ADRs, `SCOPE.md`, `CLAUDE.md`, `docs/STATUS.md`, `MVP_v1.md`, the commit history `e1c66f7..HEAD` (97 commits, 2026-06-02 → 2026-06-09), and the sibling repos `wegofwd-llm` (latest tag `v0.1.1`, 773 LOC / 48 tests) and `pramana` (HEAD `e2958ef`, branch `feat/ai-drafted-approved-content`; a definitive cross-repo grep confirms Pramana does not yet import the seam). Where `CLAUDE.md`/`SCOPE.md`/`docs/STATUS.md` conflict with the ADRs or the code, the code and ADRs were treated as authoritative. Supersedes v1.0 (2026-06-02 @ `e1c66f7`).*
