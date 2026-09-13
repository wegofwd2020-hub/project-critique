# Kathai Chithiram — Scoping, Design, Architecture & Development Pattern

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/kathai-chithiram` |
| Branch | `main` |
| Git commit | `e19ca0d` (as of 2026-09-13) |
| Product version | 0.1.0 |
| Doc updated | 2026-09-13 |
| Last deployed | TODO — set last deployment date-time (not in git) |
<!-- doc-meta:end -->

**Reviewed:** 2026-09-13 (v1.0 — first review, against `main` at `e19ca0d`)
**Related:** [kathai-chithiram-critique.md](kathai-chithiram-critique.md) · [kathai-chithiram-practices.md](kathai-chithiram-practices.md)

---

## 1. The Problem Being Solved

A parent of a special-needs child writes, in their own words, a small story — a routine, a coming change, a social situation the child finds hard. The product turns that into a **calm, captioned, short animation the child can actually watch and understand**. The hard part is not the animation; it is that the input is special-category personal data about a vulnerable person, the output is shown to that vulnerable person, and a mistake in either direction (a frightening image, a leaked name, a medical-sounding claim) is a real harm, not a bug. Every scoping and design decision below is downstream of that single fact.

The September 2026 reframe (`docs/STATE_OF_PLAY.md`, ADR-009) widens the *vision* to a "context dictionary" — a citation-grounded, never-advise knowledge asset for people with disabilities and their carers, of which the animation is "Surface 1." That vision is written but unbuilt; the built product is the animation pipeline, and this document reviews the pattern of *what shipped*.

## 2. Scoping Pattern

### 2.1 The safety floor is the first design decision, stated as a hard constraint
Before the pipeline, the ADRs. ADR-001 fixes the rule that "automation is never the sole safeguard," and the whole architecture is built to satisfy it: a human review gate that *cannot be bypassed*, three independent automated safety layers underneath it, and a privacy regime that assumes the worst about every egress. The safety floor is not a feature added late; it is the constraint the rest of the code is shaped to fit.

### 2.2 Scope is drawn by *data risk*, and capabilities are built-but-gated rather than deferred
The progress engine (M1) is the clearest example: the mechanism is fully built (`progress/engine.py`, `progress/policy.py`) but ships **no thresholds and no defaults**, requires an explicit `--policy` and a therapist role, and therefore "does nothing until a reviewed policy exists." The team chose to build the inert mechanism and gate it on a clinician, rather than guess at the policy. Same with accounts+DOB: the onboarding commands exist and store only age bands, tested against synthetic identities, but real child data is gated on DPO sign-off.

### 2.3 The vision was allowed to outrun the code — deliberately, and labelled as such
ADRs 006–013 (context dictionary, practice assistant, commercial model, trained domain model) were authored in a September documentation sprint and are all *Proposed*; `ADR_INDEX.md` states plainly that none is built. This is a scoping choice: write the decisions down so the direction is unambiguous, but do not let strategy prose masquerade as shipped capability. The honesty is the redeeming feature — the risk is that a casual reader takes the vision for the product.

## 3. Design Pattern

### 3.1 One narrow LLM seam; everything that can be deterministic is
The design axis is "deterministic where it matters, smart where it helps." Generation (story→scene-script) is the *only* place a model is consulted; validation, rendering, safety guards, offline generation, template authoring, and progress measurement are all pure. The model's output is a dict of strings that a deterministic validator immediately gates — so a bad generation is a rejected script, never a bad render.

### 3.2 The scene-script is the contract, and every producer targets it
v1/v2 JSON schemas define the scene-script; v2 closes the vocabulary (fixed settings/props/poses/expressions). Three different producers — the LLM, deterministic `--offline` segmentation, and `author` template lowering — all emit the same contract, and the renderer consumes only the contract. This is contract-over-coupling inside a single repo: the generation strategy is swappable because the interface between "make a script" and "draw a script" is a validated document, not a function call.

### 3.3 Pseudonymize before egress, reinsert at the last possible moment
The child's name becomes a token (`CHILD`) before generation and is reinserted only at render time. The name never enters a prompt, a log, an audit record, or storage in the clear. The design treats the LLM boundary as hostile and minimizes what crosses it, with a hard stop (`IdentifierLeakError`) if minimization fails.

### 3.4 Fail closed, everywhere it matters
The zero-retention credential raises rather than falling back to an ambient key; a provider lacking no-training/zero-retention is refused; grounding retrieval that raises degrades to *ungrounded* (safe) rather than erroring the whole generation; unsafe render output is never promoted from draft to final. The default on every safety-relevant branch is "refuse or degrade safely," not "proceed."

## 4. Architecture Pattern

### 4.1 A linear, gated pipeline with a human in the middle
`intake+consent → pseudonymize → generate (validate-and-repair) → [ground] → validate → store (encrypted) → render → guard → human review → deliver`. Each arrow is a gate that can stop the flow: consent missing → `ConsentError`; identifier leak → `IdentifierLeakError`; invalid script → `SceneScriptInvalidError`; unsafe frames → never promoted; no reviewer sign-off → never delivered. There is no path from raw story to delivered animation that skips a gate.

### 4.2 The seam pattern is used three times, at three maturities
- **`wegofwd_llm/`** — a *local vendored* seam (a `Protocol` + an Anthropic provider), not the external shared package the README implies. Good design, mislabelled provenance.
- **`wegofwd-video`** (ADR-026) — a *genuine external* dependency (pinned to tag `v1.0.0`); kathai registers its own renderer as a `deterministic-renderer` provider and drives it through the registry + provenance API, in-process so child content never leaves.
- **`wegofwd-arivu`** — a *genuine external* dependency (pinned to an immutable SHA) behind the optional `[grounding]` extra, consumed by KC-21 retrieval grounding.

### 4.3 Safety is layered, not centralised
Rather than one "safety module," the guards sit at each layer they can act on: content *rules* at generation (prompt), *structure and grammar* at validation (deterministic), *technical harm* at render (fps/flash/audio), and *meaning* at the human gate. No single layer is trusted to be sufficient — which is the ADR-001 principle made architectural.

## 5. Development Pattern — Contact With Reality

The git history (307 commits, 119 merges, PRs to #102, 2026-04→2026-09) shows a **spec-first, SDD, reviewed-PR** workflow that is real, not claimed:

- **Spec→plan→implementation triads are visible in the log.** KC-21: `docs: spec` → `docs: implementation plan` → `feat(grounding): GroundingSource seam` → … → `Merge: KC-21`. Same shape for KC-12. Six `docs: spec` commits.
- **Subagent-driven development is on disk.** `.superpowers/sdd/` holds a `progress.md` ledger and per-branch review diffs; the ledger records task-by-task completion with reviewer verdicts ("Final whole-branch review (opus): Ready to merge = Yes… 677 full suite pass, mypy 0, ruff clean").
- **Cadence is bursty, not steady** — two intense sprints (July = 194 commits, September = 78) around a nearly dormant August (1 commit). Feature work compounds inside a sprint; the calendar between sprints is idle.
- **The recent edge is documentation, not features** — the last ~20 commits are the KC-21 grounding merge followed by a strategy/system-map documentation consolidation. The vision layer was the most recent investment.

The gap between this disciplined pattern and the shipped state is the *enforcement* layer: the SDD ledger says "ruff clean" at a past branch tip, but `ruff check .` fails today at `generator.py:120`, and there is no CI to have caught the regression. The discipline is real and self-imposed; it is not machine-guaranteed.

## 6. Key Decisions and Their Rationale

### Decision 1 — Make "automation is never the sole safeguard" the top constraint (ADR-001)
Rationale: the cost of a bad output is a harm to a vulnerable child, so no automated layer, however good, is trusted alone. Cost if wrong: a mandatory human gate caps throughput and rules out a hands-off service — accepted deliberately.

### Decision 2 — One LLM seam, everything else deterministic
Rationale: minimize the surface where non-determinism (and a third party) can affect a child's output; make the model's blast radius a dict a validator gates. Cost: richer, model-driven rendering is off the table by construction.

### Decision 3 — Build capabilities inert and gate them on a named person
Rationale: the progress engine and accounts need a *clinician's* and a *DPO's* judgement that the team cannot honestly supply; building the mechanism but shipping no policy avoids guessing at safety-critical defaults. Cost: visible "built but does nothing" surfaces that read as incomplete to an outsider.

### Decision 4 — Write the whole vision down as ADRs before building it
Rationale: keep direction unambiguous and reversible on the merits (ADR-010 explicitly reverses ADR-006 for one track). Cost: a large *Proposed*/unbuilt ADR set that outpaces the code and can be mistaken for shipped capability if the status vocabulary is ignored.

## 7. What This Pattern Teaches

### Lesson 1 — A safety floor stated as a constraint shapes better architecture than one added as a feature
Because "no single automated layer is sufficient" was fixed first, the guards ended up *distributed across the layers that can act on them* rather than piled into one bypassed "safety module." The constraint produced the layering.

### Lesson 2 — "Built but gated" is an honest way to handle a decision you are not qualified to make
Shipping the progress engine with no policy, gated on a clinician, is more honest than shipping a guessed threshold — and more useful than deferring the code entirely, because the mechanism is ready the day the policy arrives.

### Lesson 3 — Self-discipline is not enforcement, and the difference is visible
A repo with strict mypy, a hand-written ruff rule, an SDD review ledger, and 735 tests still fails its own linter on the rule it wrote — because nothing runs the check on merge. Local tooling is only as good as the CI that makes it non-optional. This is the single highest-leverage fix here, and it is an afternoon of work.

### Lesson 4 — Label provenance as carefully as you label status
The ADR status vocabulary (Proposed/Accepted) is exemplary; the "shared `wegofwd-llm` package" claim and the cited-but-absent ADR-026 are the opposite — a reader cannot tell a vendored copy from a shared dependency, or follow a governance reference that does not exist in the repo. The same honesty applied to *status* needs applying to *dependencies and citations*.
