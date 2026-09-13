# Pramana — Scoping, Design, Architecture & Development Pattern

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/pramana` |
| Branch | `main` |
| Git commit | `f23749f` (as of 2026-09-10) |
| Product version | 0.1.0 |
| Doc updated | 2026-09-13 |
| Last deployed | TODO — set last deployment date-time (not in git) |
<!-- doc-meta:end -->

**Reviewed:** 2026-09-13 (v1.0 — first review, against `main` at `f23749f`)
**Related:** [pramana-critique.md](pramana-critique.md) · [pramana-practices.md](pramana-practices.md)

---

## 1. The Problem Being Solved

An organisation subject to a compliance regime (v1: SOX, for a single named corporate client) must *prove*, to an auditor, that named people completed required training on a specific version of specific content, and that the record cannot have been altered after the fact. The training itself is the easy part; the hard part — and the reason this product exists — is producing **evidence an auditor will accept**: tamper-evident, version-pinned, and reconstructable from first principles. Pramana is designed so that the audit trail, not the course, is the primary artifact. Every scoping and architecture decision below follows from treating "the evidence must survive scrutiny" as the top constraint.

## 2. Scoping Pattern

### 2.1 Compliance-as-architecture, decided first
The founding decision (`docs/02_resolved_decisions.md`) is that compliance is structural: a SHA-256 hash-chained, append-only audit log with database-level immutability, and evidence pinned to content versions. This is fixed before features, and the features are shaped to feed it. The audit hash being a *pure, re-computable* function is the tell — it means an auditor can independently verify the chain, which is the whole point.

### 2.2 Scope narrowed to one framework, one tenant, deliberately
v1 is SOX-only, single-tenant, for one named client. FCPA and four other frameworks (GDPR/HIPAA/ISO/PCI) exist as *authored story libraries and framework references*, not validated runtime scope — marked "future phase." The engine is regulation-agnostic (a framework is parsed data, "none of them know what SOX is"), so the narrowing is a go-to-market scoping choice, not an architectural limit. Multi-tenancy is carried in the schema (`tenant_id` everywhere) but its enforcement is deferred — the column is present so the later decision is cheap, the isolation is absent because v1 doesn't need it.

### 2.3 "Feature-complete" was scoped as code-complete, and labelled honestly
`project-status.yaml` marks all ~24 features `done`, and a test enforces the README status table against it. But "done" is explicitly code-complete, and the same manifest says "not yet deployed." The scoping discipline here is that *completeness and deployment are tracked as separate axes* — a distinction most solo projects blur, and the one that keeps this project honest about being pre-launch.

## 3. Design Pattern

### 3.1 The evidence is immutable by construction, not by policy
Append-only is enforced by DB triggers, not application discipline — and when the team realised row-level triggers don't fire on `TRUNCATE`, they added statement-level `BEFORE TRUNCATE` triggers (migration `0011`) rather than documenting a caveat. The design consistently prefers a mechanism that *cannot* be violated over a rule that *should not* be.

### 3.2 Two state machines, pure and separated
Assignment lifecycle and content approval are each modelled as explicit, pure state machines with property-based tests. Content approval enforces **separation of duties** (the producer of a video cannot attest it) and a distinct video-fidelity attestation gate. Keeping these pure (no I/O, no clock in the transition logic) is what makes them property-testable and what keeps the compliance-critical rules in one auditable place.

### 3.3 Seams are Protocols with fail-closed defaults
LLM and video are `Protocol` interfaces injected into pure-domain functions; the defaults are `Null`/fake providers, and real provider construction *raises* without a key. The consequence is that the entire loop is runnable and testable with zero model calls — the substance of the "contracts-first, model-free" idea, even though the repo never uses the "Phase 0" label the portfolio strategy applies to it.

### 3.4 Determinism as a compliance property
The `render` extra pins `torch==2.14.0`/`transformers==5.16.1` exactly, with a long comment arguing reproducibility is a compliance requirement, not tidiness. The design treats "the same input produces the same evidence" as load-bearing — which makes the *absence of a top-level lockfile* (§Pattern-vs-practice below) the one place the principle isn't followed through.

## 4. Architecture Pattern

### 4.1 A four-stage content loop feeding an evidence spine
`Create → Manufacture → Approve → Present`: a content request validated against the definitions library → ingestion of a signed package as an untrusted `RECEIVED` draft → the approval state machine (with separation-of-duties + video attestation) → publish, which materialises an *immutable* `CourseVersion` + questions/answers. Then `Assign → Play → Grade → Prove`: assignment pins the active version, the player gates the quiz on watch-percentage, grading is server-side and carries prior-correct answers forward, a pass issues a verifiable certificate, and `/audit` + `/evidence` produce the proof. Every stage writes to the audit spine.

### 4.2 The shared engine, specialised for auditability
Pramana consumes the family engine — `wegofwd-llm` (`v0.1.1`) and `wegofwd-video` (`v1.1.0`) — as **external git-pinned packages** (not vendored, in contrast to kathai-chithiram's local copy of the LLM seam). It is the **generative/Veo consumer** of `wegofwd-video` (`narrative-video` (Veo) + `local-preview` (LTX on CPU)), where kathai is the deterministic-renderer consumer. Pramana specialises the generic seam for *auditable, human-approved* content: the video seam is wrapped in a two-gate attestation control unique to the compliance use case — AI output arrives as an untrusted draft that a separate human must attest before it can publish.

### 4.3 Deployment is a gated, fail-closed pipeline
A container stack (`postgres:16` → one-shot Alembic `migrate` → `api` bound to `127.0.0.1`) plus an SSH auto-deploy workflow gated behind `PRAMANA_DEPLOY_ENABLED`, with a pinned host key (no TOFU), a retrying smoke test, an incident issue on failure, and — deliberately — no auto-rollback, because a bad migration is not fixed by redeploying. The operational design mirrors the domain design: prefer fail-closed and human-in-the-loop over automatic recovery that could paper over a data-integrity problem.

## 5. Development Pattern — Contact With Reality

The git history (190 commits, 42 merges, PRs to #49, May→Sep 2026, bursty with Sept ≈ 103) shows a **near-textbook spec-first + SDD + TDD** workflow, and one moment of genuine contact with reality that is the most instructive event in the whole review:

- **Spec→plan→implementation triads are explicit** (e.g. consumer-subscription: design spec → implementation plan → status-manifest record; the video pilot: scope/ticket → implementation plan → PR). Plans invoke `superpowers:subagent-driven-development` **by name**, and every task is written failing-test-first *in the plan* before code.
- **Plans were reviewed and corrected pre-dispatch** — commits like "fix two defects in Task 5's tests before dispatch" and "correct Task 6's harness against the real wegofwd_video API" show the plan being debugged against reality before an implementer ran it.
- **The SOX video pilot's gate fired on first real input.** A human product owner **refused attestation** of the first generated lesson — it was silent, cartoonish, and had hallucinated on-screen text; the refusal is recorded verbatim in the pilot log. The team then root-caused it (the prompt template summoned caption-laden stock footage, not a guidance failure) and partially unblocked it. This is the pattern working exactly as designed: an automated pipeline produced plausible-looking output, and a *mandatory human attestation gate stopped it from shipping*. The project treats the refusal as the pilot's success, and documents it as such.

The gap between this exemplary pattern and the shipped state is deployment and one hard content problem: the pipeline is feature-complete and CI-green, but it has never been stood up in production, and the video lesson — the artifact the pilot exists to prove — has not yet cleared a human's fidelity bar.

## 6. Key Decisions and Their Rationale

### Decision 1 — Make the audit trail the product (compliance-as-architecture)
Rationale: an auditor accepts evidence, not courseware; tamper-evidence must be structural to be defensible. Cost: heavier write path (every mutation appends to a hash-chained log) and immutability constraints that complicate any later "edit history" feature — accepted deliberately.

### Decision 2 — External git-pinned engine, not vendored
Rationale: pramana is a *consumer* of the family LLM/video seam; pinning to tags (`v0.1.1`/`v1.1.0`) keeps it aligned with the shared contract without owning the code. Cost: reproducibility depends on those tags + the network, and there is no lockfile to freeze the transitive tree.

### Decision 3 — Human attestation gate on all AI-generated content
Rationale: AI output is an untrusted draft; for compliance content a human must own the "this is accurate and appropriate" claim, with separation of duties so the producer can't self-attest. Cost: throughput is capped by human review, and it is exactly this gate that has (correctly) blocked the video pilot from shipping.

### Decision 4 — Ship "feature-complete but not deployed," tracked as separate axes
Rationale: the honest state is that code is done and go-live is gated on external commitments (a client, legal sign-off, infra); conflating the two would misrepresent readiness. Cost: a status manifest that reads "all done" next to "not deployed," which can mislead a skim-reader — mitigated by the drift-tested README summary.

## 7. What This Pattern Teaches

### Lesson 1 — Enforce integrity with mechanisms, not rules, and chase the edge cases
Append-only via triggers beats append-only via convention — and the `TRUNCATE` fix shows the difference is only real if you find the edge where the mechanism doesn't fire. A compliance guarantee is only as good as its least-covered bypass.

### Lesson 2 — A human gate that fires is a feature working, not a failure
The video pilot's most valuable output was a *refusal*. Building the attestation gate so that plausible-but-bad AI output cannot ship — and then documenting the refusal in the reviewer's own words — is the compliance posture done right. The lesson is to treat "the control stopped us" as the success signal it is.

### Lesson 3 — Track completeness and deployment as separate axes
"All features done" and "not deployed" are both true here, and saying so plainly is what keeps the project honest. Most solo projects collapse these into one optimistic word; pramana's separation (with a drift test binding the manifest to the README) is a practice worth copying.

### Lesson 4 — Test the mechanism that carries the value
The one place the discipline slips is telling: migrations — the durability of the audit schema that *is* the product — are the one thing CI never runs (tests build the schema from ORM metadata instead). The lesson is to point the strongest testing at the mechanism the product's value depends on, which here would be `alembic upgrade head` in CI, not `create_all`.
