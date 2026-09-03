# AGASTYA — Scoping, Design & Development Pattern

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/agastya` |
| Branch | `main` |
| Git commit | `2abde5a` (as of 2026-08-10) |
| Product version | —  (commit-based; no release version) |
| Doc updated | 2026-09-03 |
| Last deployed | not deployed — live demo in progress (blocked on DNS) |
<!-- doc-meta:end -->

**Document type:** Development-pattern analysis (methodology only)
**Scope:** How a FastAPI cyber-monitoring package was *scoped, verified, hardened, and deployed* — the lifecycle and method, not the detection internals.
**Period:** v1.0 — first review, against `origin/main` at `2abde5a` (2026-08-10), measured 2026-09-02.
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Related:** `agastya-practices.md`
**Note on what this document is and isn't:** AGASTYA's most instructive property is not its code — it is the *method by which an inherited, AI-generated codebase was adopted*. This document analyses that method: a three-sub-project spec-driven effort to import, verify, correct, and deploy a package the team did **not** author and had explicit reason not to trust. It contains no security assessment; the four-lens critique for this product is held privately, because it is a live-intended cyber-detection system.

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern (as a method)](#4-architecture-pattern-as-a-method)
5. [Development Pattern](#5-development-pattern)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

Most of this portfolio's products were scoped and built from a blank page. AGASTYA was not. It arrived as a **delivered artifact** — a ~7,000-line FastAPI package generated elsewhere, handed over with a confident claim ("production-ready, 41+ tests passing") that turned out to be **false on contact**: the test suite did not even collect. The genuine problem, then, was not "design a threat monitor." It was:

```
The problem in one frame
─────────────────────────

  "You have been handed a large codebase you did not write, whose author's
   quality claims are demonstrably unreliable. Turn it into something you can
   put your name on and stand up in public — without pretending it is more
   than it is, and without silently inheriting the author's mistakes."
```

That is a **software-adoption** problem, and it has a different shape from a build problem. The hard parts are epistemic (what does this code *actually* do, versus what does it *claim*?) and dispositional (what do you fix, what do you leave, what do you refuse to ship as stated?). AGASTYA's development pattern is the answer this project reached, and it is reusable well beyond this one repo — because AI-generated deliveries with inflated self-descriptions are now a common input, not a rare one.

---

## 2. Scoping Pattern

### 2.1 The work was cut into three sequential sub-projects, each with its own spec

Rather than treat "adopt AGASTYA" as one amorphous task, it was scoped into three independently-specified sub-projects, gated in order:

```
  1. The repo   → import the package into a clean, tested private repo
  2. The page   → a public /work showcase page (separate spec)
  3. The deploy → a live, read-only demo on a VPS (separate spec)
```

Each carried its own `docs/superpowers/specs/…-design.md` and `…-plan.md`. The value of the split is that it front-loads the one question that governs everything downstream — *is the code even sound enough to build on?* — into sub-project 1, before any effort is spent on a page or a deploy. If the import had failed verification, the later sub-projects would never have started.

### 2.2 The scope boundary was drawn as "rehabilitate, don't rewrite"

The repo-import spec makes an explicit, unusual scope call: **"any refactor of the AGASTYA code itself" is out of scope.** The team would import the package, make its tests pass, fix delivered defects that broke the build, and wrap it for deployment — but it would *not* re-architect the detection code. This is subtractive scoping applied to inherited code: the boundary is a line drawn *around* someone else's work, deciding how deep the intervention goes.

The trade-off was accepted knowingly. Leaving the code un-refactored means inheriting its structure — including whatever the author left shallow or unwired. The discipline is that this is a *stated* boundary, not an accident: the spec names it, so the reader knows the import was a triage-and-ship, not a rebuild.

### 2.3 The "flat import" problem was solved at the seam, not by touching 19 files

A concrete instance of the same principle. The delivered modules use flat imports (`from models import …`) despite living in a package directory — so they only resolve with that directory on `sys.path`. The spec's "key finding driving the layout" section diagnoses this and fixes it at the **configuration seam** (a `pythonpath` entry in `pyproject.toml` for tests; a `WORKDIR` in the Dockerfile for runtime) rather than rewriting the import statements in every module. Lowest-risk, zero code change, and consistent with the "rehabilitate, don't rewrite" boundary. The pattern: when inherited code has a structural quirk, prefer the smallest external accommodation over an invasive edit whose blast radius you can't fully predict.

---

## 3. Design Pattern

### 3.1 Verify-don't-trust as the governing discipline

The defining design commitment is stated in the spec and honored in the commits: **the delivered "41+ tests passing" claim was treated as discredited, and re-established from scratch.** The acceptance gate was not "the author says it passes" but "`pytest` runs from the repo root and we report the output verbatim." That single move — refusing to inherit a quality claim, and instead re-deriving it — is what surfaced that the suite didn't collect, and then that several delivered defects existed beneath it. Seven latent defects were found and fixed during the import, each with a regression test added alongside the fix.

The reusable idea: **a claim about code is not evidence about code.** For an AI-generated delivery especially, the self-description is the least reliable artifact in the box. The method is to reconstruct the ground truth (does it build? do the tests collect? do they assert real behavior?) before building anything on top.

### 3.2 Honesty in the surface: relabel to match reality

Where the delivered docs oversold, the import corrected the *reader-facing* surface: the README was rewritten to state plainly that the system "ships with mock data" and that its default mode exposes the full read/write API. This is a design choice about *representation* — the code was left as scoped, but the description of it was pulled back to the truth. The principle is that when you adopt something you didn't build, the honest move is to make its public description match what it is, even when you're not re-building what it is.

### 3.3 The demo as derived output, not a hand-made fixture

A deliberate design decision in the deploy sub-project: the public demo's data is produced by replaying canned scenarios **through the same code path the live endpoint uses** (a shared `process_event` function, extracted precisely so the two cannot diverge). The design rule is that a demo should be *evidence of what the system does*, generated by the system, rather than a curated JSON file that can drift into flattering fiction. If the underlying logic breaks, the demo breaks visibly at boot — which is the point.

### 3.4 Fail-closed seeding and fail-closed posture

Two design commitments in the same spirit. The demo seeder refuses to start if seeding leaves any store empty (a demo serving empty lists *looks* healthy while being useless — so a silent content failure is converted into a visible crash-loop). And the read-only posture for the public deploy is made the **image's default**, not a property of an external config file that a bare container run could bypass. Both are instances of one design rule: make the safe state the default, and make the unsafe state loud.

---

## 4. Architecture Pattern (as a method)

*Architecture is discussed here only as it bears on the adoption method; the running system's internals live in the private critique.*

### 4.1 Extract the shared seam before you build two consumers of it

The clearest architectural move of the effort was to **extract a single pipeline function** and have both the live API and the demo seeder call it. This was done as its own planned task, with a renumbering of the task list to accommodate it (`refactor: extract the shared event pipeline`). The method lesson is that when two features must provably do the same thing (here: "the demo must run what the endpoint runs"), the architecture should *make divergence impossible* by construction — one function, two callers — rather than relying on the two to be kept in sync by discipline.

### 4.2 Deploy as a layered, defense-in-depth wrapper around unchanged code

The deploy sub-project wraps the un-refactored package in layers — an env-gated read-only mode inside the app, a route-and-schema strip so the app's own advertised surface matches, a hardened container (non-root, byte-code-off, a real health check, single-worker with a documented reason), and a reverse proxy above all of it. The method: when you cannot change the core, you **build the guarantees you need around it in layers**, each independently correct, so that no single layer is load-bearing alone.

---

## 5. Development Pattern

### 5.1 SDD cadence: spec → plan → numbered tasks → whole-branch review

Each sub-project followed the same superpowers loop visible in the commit arc: a design doc, an implementation plan, a set of numbered tasks executed one per (roughly one) commit, and — critically — a **whole-branch review at the end** that produced its own corrective commits (`fix: close cross-task gaps found in whole-branch review`, `docs: repair drift found in whole-branch review`). The task list was re-planned mid-stream when a new need appeared (extracting the pipeline; adding a suppression-rule fix task), and the plan docs were updated to match rather than letting the plan and the work drift apart.

### 5.2 The commit arc is a rehabilitation record, not a creation record

42 commits over ~2 days, and their messages tell the method rather than the feature set: `import v1.5 package (curated)`, `repair delivered bugs so the full test suite passes`, `README says 64-test suite (was the discredited '41+' delivery claim)`, `guard demo seed against double-seeding`, `env-gated demo mode that strips mutating routes`, `container definition for the read-only demo`, `watchdog for the unhealthy-but-running gap`. Reading the log top to bottom is reading a triage: import, verify, correct, wrap, deploy, observe. This is the signature of the pattern — the git history documents *adoption*, not authorship.

### 5.3 Correction commits are first-class and self-documenting

A notable discipline: when the work corrected its own earlier claims or specs, it committed the correction explicitly — `docs: spec overclaimed the seed as deterministic`, `docs: correct EventType.MALWARE -> MALWARE_SIGNATURE in Task 2 test`, `docs: studybuddy port exposure is fixed, not open`. The method treats "we said something inaccurate earlier" as a thing you fix in the open, with a commit that names the inaccuracy — the same verify-don't-trust discipline turned on the team's own output.

---

## 6. Key Decisions and Their Rationale

### Decision 1: Adopt via a three-sub-project SDD split, gated on the import
**Why:** the riskiest question (is the delivered code sound?) is answerable in the first sub-project alone; gating the page and deploy behind it means no effort is spent downstream of a codebase that couldn't pass verification.
**Trade-off:** more up-front spec overhead than a single "get it deployed" task — paid back by never building on unverified ground.

### Decision 2: Rehabilitate, don't rewrite — a stated scope boundary
**Why:** re-architecting ~7k lines of inherited code is a large, high-risk effort with unclear payoff for a showcase artifact; a triage-and-ship gets it into a reviewable, deployable state fast.
**Trade-off:** the artifact inherits the author's structure, including whatever is shallow or unwired. The mitigation is that the boundary is *named* in the spec, so the disposition is honest.

### Decision 3: Treat the delivered quality claim as discredited and re-verify from zero
**Why:** the "41+ tests passing" claim was false; an AI delivery's self-description is the least trustworthy artifact in it. Re-establishing ground truth is the only sound basis for building on it.
**Trade-off:** verification found real defects that then had to be fixed (cost that a clean component wouldn't carry) — but that cost was the *point*, not a surprise.

### Decision 4: Extract a shared pipeline so the demo cannot lie
**Why:** a showcase demo is only evidence if it runs the real code path; making the demo and the endpoint share one function removes drift by construction.
**Trade-off:** one extra refactor task inside a "don't refactor" boundary — accepted because it serves honesty, and it was planned and committed as its own explicit task.

### Decision 5: Make the safe posture the default, loudly
**Why:** for a public deploy of a system with a full read/write API, the read-only posture must not depend on an external file a bare run could skip; and an empty-but-healthy demo must fail rather than mislead.
**Trade-off:** slightly more machinery (image-baked env, route strip, seed guard) than a config-file toggle — justified by defense in depth.

---

## 7. What This Pattern Teaches

### Lesson 1 — Adopting AI-generated code is its own discipline, distinct from building
The reusable core of AGASTYA is the *adoption method*: import into a clean repo, re-verify every quality claim from zero, fix what the verification surfaces, draw and state a scope boundary, and wrap for deployment in independently-correct layers. As AI-generated deliveries with confident, inaccurate self-descriptions become a normal input, this triage pattern is more broadly useful than any single feature build.

### Lesson 2 — A claim about code is never evidence about code
The delivered "41+ tests passing" was false, and the method that caught it was refusing to inherit it — re-running the suite and reporting the output. The teaching generalizes: for any handed-over artifact, reconstruct the ground truth (builds? collects? asserts real behavior?) before trusting a word of the description. This is doubly true for machine-generated code, whose prose is generated with the same confidence whether or not it matches the code.

### Lesson 3 — Fix at the smallest seam that solves the problem
The flat-import quirk was solved with a config line, not a 19-file edit; the read-only posture with an image default, not a code rewrite. When you're working inside someone else's structure under a "don't rewrite" boundary, the smallest external accommodation that is *provably* sufficient beats the invasive change whose blast radius you can't see.

### Lesson 4 — Make divergence impossible, not merely discouraged
"The demo must run what the endpoint runs" was guaranteed by one shared function with two callers, not by a promise to keep them in sync. Whenever two things must behave identically, the architecture should collapse them to one implementation — the method's job is to remove the *possibility* of drift, not to police it.

### Lesson 5 — When you adopt it, own the honesty of its description
The strongest single act in the effort was pulling the reader-facing surface back to the truth: "ships with mock data," "runs the full read/write API by default." You may inherit code you can't fully re-build, but you always control how it is described — and matching the description to reality is the part of adoption that is never out of scope.

---

*Analysis based on `origin/main` at `2abde5a`, grounded in the superpowers specs and plans under `docs/superpowers/`, the 42-commit history, the README, and a full read of the wired source. This document is methodology only; the security assessment, ratings, and cost triangulation for AGASTYA are maintained privately, as befits a live-intended cyber-detection product. Companion (public): `agastya-practices.md`.*
