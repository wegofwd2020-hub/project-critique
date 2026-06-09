# StudyBuddy SelfLearner (Mentible) — Scoping, Design, Architecture & Development Pattern

**Document type:** Development pattern analysis
**Scope:** Full lifecycle — from advisor feedback to pre-deploy MVP
**Period:** 2026-04-25 → 2026-06-01 (~5 weeks, 131 commits)
**Last refresh:** 2026-06-02 (v1.0 — first analysis; measured on disk at `e1c66f7`, branch `feat/authoring-regenerate-export-fixes`)
**Repo / brand:** `wegofwd2020-hub/StudyBuddy_SelfLearner` · public brand **Mentible** (*"Author Yourself"*)
**Related:** [studybuddy-selflearner-critique.md](studybuddy-selflearner-critique.md) · [studybuddy-selflearner-practices.md](studybuddy-selflearner-practices.md) · [studybuddy-selflearner-cost.md](studybuddy-selflearner-cost.md) · parent product: [studybuddy-development-pattern.md](studybuddy-development-pattern.md)
**Author:** WeGoFwd2020 / Claude (Anthropic)

> This is the development-method analysis: *how* the product was scoped, designed, and built — less about bugs (see the critique), more about the decision discipline. The defining trait of this project is that it is **ADR-driven and spec-first to an unusual degree**, and it re-scoped its own product definition twice in five weeks without thrashing the codebase.

---

## 1. Origin — a product born from a GTM critique

Most products start from a feature idea. Mentible started from a **go-to-market objection** to a *sibling* product.

After the first StudyBuddy_OnDemand demo (2026-04-25), an advisor said, in effect: *the content-generation IP is the valuable core; the school/district go-to-market is the expensive part — consider a thin interface that lets a user access the generation directly.* `SCOPE.md §2.1` preserves the feedback verbatim. The entire product is a structured response to that one sentence:

- Keep the IP (the six scope dimensions that turn a bare prompt into a real educational artefact).
- Drop the expensive plumbing (multi-tenancy, RLS, FERPA/COPPA, schools, classrooms, Stripe, Auth0).
- Shift the token cost to the user (**BYOK**) so the vendor never carries an Anthropic bill.

The scoping method here is worth naming: **subtractive scoping from a working sibling.** Rather than greenfield design, the team took an existing, validated system and asked "what is the smallest surface that preserves the moat and discards the cost?" `SCOPE.md §8` is an explicit "carried over / NOT carried over" ledger — Auth0, RLS, multi-tenant DB, curricula/schools/Stripe, COPPA/FERPA are all listed as deliberately *not* carried. That ledger is the design.

---

## 2. The scoping artifact — a decision table, not a doc

`SCOPE.md` is not prose; it is a **decision register**. Nineteen locked decisions (D1–D19), each a one-line rule with a rationale, plus an "open decisions" section (§6) where each open question is answered inline with the founder's choice ("Let us go with B", "Minutes", "confirming refined input list"). The pattern: **every open question is closed in the same document, in the founder's own words, before code starts.**

| Decision | Choice | Why it mattered to the build |
|---|---|---|
| D1 | BYOK | The whole security architecture (ADR-001) follows from this |
| D9 | Key handling Pattern B (per-request passthrough) | Defined the Redis envelope + TTL + shred design |
| D8 | React Native / Expo | Cross-platform path; matches OnDemand's Epic 3 Path B |
| D2/D12 | Async generation + push, latency "minutes" | Justified a job queue + polling rather than a streaming UI |
| D13 | v1 formats: Lesson / Explanation / Quiz | Scoped the prompt + schema surface |
| D5/D6 | New repo, no funnel to the school SKU | Forced vendoring instead of a shared runtime |

This is **spec-driven development taken literally** — the repo even ships `Spec-Driven-Development-For_Dummies.md` as a method artifact. The lesson the project is teaching itself: *decide on paper, in a register, before you write code.*

---

## 3. The defining pattern — ADR-driven re-scoping without code thrash

The most instructive thing about this project is that it **changed what the product fundamentally is, twice, in five weeks** — and each pivot was a *decision artifact*, not a rewrite.

| ADR | Status | What it changed |
|---|---|---|
| ADR-001 | Accepted | BYOK security model, Pattern B — the per-request passthrough contract |
| ADR-002 | Accepted | Repo structure & vendoring (Approach C) — copy, don't import; record SHAs |
| ADR-003 | Proposed | "Q grows up" — adds **book authoring**; books are **local-first** |
| ADR-004 | Proposed | **Two-product split**: paid authoring app (this repo) + separate free reader; **EPUB3 becomes the delivery artifact**; the app becomes **paid** (revising D17) |
| ADR-005 | Accepted (unbuilt) | Multi-provider LLM + **hybrid keys** (managed-key default, BYOK power-user); pulls accounts/metering forward |
| ADR-006 | Accepted | **Rebrand** "StudyBuddy Q" → **Mentible** ("Author Yourself") |

The pattern: **a scope-defining decision gets a numbered, dated ADR; superseded options are explicitly closed.** When the "author a book" idea grew large enough to be its own product, the team didn't bolt it onto either existing app — ADR-004 drew a new product boundary, and *OnDemand's own ADR-002/ADR-003 were closed without merge* (recast here). That is the healthy version of pivoting: the losing options are retired in writing, so the next contributor doesn't re-litigate them.

**The risk this pattern creates** (and the critique flags): the ADRs moved faster than `SCOPE.md`/`CLAUDE.md`/`STATUS.md`, so the top-of-funnel docs now describe an older product. The decision discipline is excellent; the *promotion* of decisions back into the durable spec lagged. ADR-velocity without spec-reconciliation is the doc-drift failure mode in miniature.

---

## 4. Architecture method — security-first, isolation by process

The architecture was argued on paper (ADR-001/002) before code, and two method choices stand out:

**4.1 Design the threat model before the feature.** Because the product's entire trust proposition is "we handle your API key safely," ADR-001 specified the full key lifecycle — HTTPS body → AES-256-GCM envelope in Redis under an HKDF-per-job key → TTL → worker reads once → shred + delete; never a log line, DB row, or traceback — *before* the `/generate` endpoint existed. The first backend test written for this code path is `test_no_key_in_logs.py`. **The security invariant was a test, not a hope.**

**4.2 Isolate by runtime, not just by module.** The compiler that turns `book.json` into EPUB3/PDF is a *separate process* (a key-free, network-free TypeScript CLI the backend shells out to). This puts the two riskiest surfaces — the secret-handling surface and the heavy-rendering (headless-Chromium/Vivliostyle) surface — in different processes. Compare OnDemand's three-runtime-context separation (pipeline/backend/client): the same instinct, applied to a smaller system.

**4.3 Vendor, don't fork; record provenance.** ADR-002 chose "Approach C": copy shared OnDemand modules into `pipeline/` with a `VENDORED.md` recording source path + SHA per file, and treat updates as a deliberate, script-driven, review-gated sync (`scripts/sync-from-ondemand.sh`). Two files (`anthropic.py`, `toc_structurer.py`) are *intentionally modified* copies — and the modifications are documented (per-call BYOK key; network wrapper removed so an error path can't stringify the key). This preserves the IP without coupling release cycles, and keeps the modification deliberate rather than silent.

---

## 5. Build sequence — thinnest vertical slice first

`SCOPE.md §11` set the first slice explicitly: *"Lesson generation, English only, no auth, single device — prove the BYOK end-to-end loop before stacking auth + cloud sync on top."* The commit history bears this out — the early work is the generate loop and the key envelope; auth, accounts, and cloud sync are deferred to v1.1+ in `CLAUDE.md` and simply not built. **Riskiest-assumption-first**: the BYOK loop is the thing that could sink the product, so it was built first.

The later commits (the `feat/authoring-*` and `feat/compiler-*` waves) show the second slice — book authoring + EPUB/PDF compilation + the Mentible visual identity — arriving as a block once ADR-003/004 settled the product shape. The sequence maps cleanly onto the ADRs: each ADR's acceptance is followed by its implementation wave.

```
Loop 1 (D1/D9, ADR-001):  BYOK /generate + envelope + redaction + tests
Loop 2 (ADR-003/004):     TOC structure → book model → per-topic generate → EPUB3/PDF compiler
Loop 3 (ADR-006):         Mentible rebrand (single brand constant), cover/colophon identity
        (ADR-005):        multi-provider/managed-key — accepted, NOT yet built
```

---

## 6. What's deferred — and how honestly

A strong method signal: the deferrals are *named*, not hidden. `MVP_v1.md` lists "intentionally fragile" gaps (no retry/queue-limit/rate-limiting/auth/sync). `CLAUDE.md` tags auth/library/sync as "v1.1+". The job runner's own docstring admits it's an in-process `BackgroundTask` standing in for the planned Celery worker, "a process restart loses in-flight jobs."

This is the right discipline (name your shortcuts) with one execution gap: some deferrals are recorded in docstrings rather than the spec, and the plan (`MVP_v1.md` says "Celery") contradicts the code (`BackgroundTask`). Naming a shortcut in three places that disagree is weaker than naming it once where the spec lives.

---

## 7. Lessons this project teaches

1. **Scope subtractively from a working system.** Mentible's design is largely a "NOT carried over" ledger against OnDemand. Knowing what to *remove* was faster than greenfield design.
2. **Close every open question in the spec, in the decider's words, before coding.** `SCOPE.md §6` is the model.
3. **Pivot with ADRs, and close the losers explicitly.** Two product-defining re-scopes in five weeks with no code thrash, because each was a decision artifact.
4. **Make the core invariant a test, not a hope.** "The key never leaks" is `test_no_key_in_logs.py` + a CI grep, written before the endpoint.
5. **Isolate risk by process.** The key-handling backend and the heavy-rendering compiler are separate runtimes.
6. **Promote decisions back into the durable spec.** The one place the method slipped: ADR-velocity outran `SCOPE.md`/`CLAUDE.md`/`STATUS.md` reconciliation — the lesson is that an ADR is only half-done until the spec it changes is updated.

---

*This analysis is drawn from the code on disk at `e1c66f7`, the six ADRs, `SCOPE.md`, `CLAUDE.md`, `MVP_v1.md`, `ARTIFACT_PIPELINE.md`, `VENDORED.md`, and the commit history (2026-04-25 → 2026-06-01). Where `SCOPE.md`/`CLAUDE.md`/`STATUS.md` conflict with the ADRs or the code, the code and ADRs were treated as authoritative.*
