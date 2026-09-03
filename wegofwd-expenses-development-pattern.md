# wegofwd-expenses — Scoping, Design, Architecture & Development Pattern

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/wegofwd-expenses` |
| Branch | `master` |
| Git commit | `aaa7fb3` (as of 2026-08-01) |
| Product version | —  (commit-based; no release version) |
| Doc updated | 2026-09-03 |
| Last deployed | TODO — set last deployment date-time (not in git) |
<!-- doc-meta:end -->

**Document type:** Development pattern analysis
**Scope:** Design & scoping methodology of a deterministic email→ledger expense pipeline
**Period:** Commit history from `2026-07-06` (repo scaffold) to `aaa7fb3` (2026-08-01) —
**36 commits on `master`** (each `fix`/`feat` paired with its own merge commit),
all measured against `origin/master`
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Related:** [wegofwd-expenses-critique.md](wegofwd-expenses-critique.md) · [wegofwd-expenses-practices.md](wegofwd-expenses-practices.md)

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern (from git history)](#5-development-pattern-from-git-history)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

A single mailbox accumulates invoices, receipts, and payment confirmations for
a portfolio of paid tools and services (LLM APIs, SaaS subscriptions,
de-identification services, and more). Reading them by hand to keep a real
expense ledger does not scale, but *automating* it with an LLM raises the
obvious objection for anything touching money: an autonomous agent that
chooses its own control flow makes a financial record non-reproducible — the
same inbox state could produce a different ledger depending on what the model
decided to do that day.

`wegofwd-expenses` answers this by refusing the premise. ADR-0001 states the
thesis directly: **pipeline, not agent.** The LLM is given exactly two narrow
jobs — classify a message, extract structured fields from one — and every
other decision (what runs next, whether a record is trustworthy enough to
post, how duplicates are detected) is deterministic code the LLM never
touches. The bet is that a financial ledger's core property, **same inputs →
same ledger**, is worth more than whatever flexibility an agent would buy, and
that the bet is cheap to honor because classification and extraction are
naturally small, bounded, and schema-validatable LLM calls.

## 2. Scoping Pattern

### 2.1 Five Stages, Chosen by Data Shape Transition, Not by Feature

The stage boundaries are not arbitrary — each one exists at a point where the
data's *shape* changes and a different concern takes over:

```
  raw email (Gmail API)         → JSONL   [mailfetch: I/O only]
  raw → {invoice|payment|...}   → JSONL   [billclassify: cheap tier + LLM fallback]
  classified → structured record → JSONL   [billextract: LLM + schema gate]
  record → durable ledger row    → SQLite  [ledger: idempotent write]
  ledger → human-readable report → Markdown [expensereport: pure read]
```

Splitting at data-shape boundaries (not at "things an LLM does" vs "things
code does") is what let ADR-0001's constraint apply cleanly: the LLM only
appears inside the two middle transitions, and each of those transitions ends
at a schema/confidence gate that the *next* stage's input is defined against
— so a stage never has to trust that the previous LLM call did the right
thing, it has to trust that the previous stage's *output validated*.

### 2.2 Subtractive Scoping: Fixtures and Contracts Before Cost

The project's own plan document is explicit about sequencing: "Tasks 1–3
(ledger + report) prove contracts on fixtures at zero LLM/network cost. Tasks
4–7 add the Gmail + LLM stages." The ledger and report stages — the two that
touch real financial arithmetic and the one output a human actually reads —
were built and proven against synthetic fixtures *before* a single line of
code that costs money or touches a live mailbox was written. This is the same
subtractive instinct atri-sangam's roadmap showed (defer what's expensive,
prove what's cheap first), applied here to development sequencing rather than
to feature scope.

### 2.3 Two Deliberately Unscoped-From-Testing Boundaries, Named Up Front

Rather than mock Google's OAuth/HTTP client or a real `pdfminer` extraction
call end-to-end, the plan named both as **out of unit-test scope from the
start**, to be exercised only against reality: "`gmail_client.py`... is
written here too but has no unit test (it is the network boundary); it is
exercised only in the Task 8 real-mailbox dry run." This is not a gap that
crept in — it is a scoping decision made in the plan document before Task 5
was written, with the interface the untested code must match (`FakeGmail`'s
shape) specified in the same sentence. The pattern is the same one atri-sangam
used for its unwired solar channel: name the boundary, build to the interface
that makes it swappable, and don't fake what you haven't built.

## 3. Design Pattern

### 3.1 On-Disk Artifacts as the Only Coupling Between Stages

No package imports another's internals. `mailfetch` writes JSONL rows;
`billclassify` reads JSONL rows and adds a `classification` field;
`billextract` reads those and adds a `record` field; `ledger` reads the
extracted JSONL and writes SQLite; `expensereport` reads only SQLite. The
`run_pipeline.sh` script is the only place that knows the file paths that
connect them. This buys the same "swap a backend without touching the engine"
property atri-sangam's `Store` protocol bought, but achieved with the simplest
possible mechanism — files on disk — appropriate to a single-user daily-batch
tool rather than a live multi-channel monitor.

### 3.2 A Schema/Confidence Gate at Every LLM Exit

Both LLM call sites — `classify_llm` and `extract_row` — end at a validation
gate before their output is trusted downstream. `classify_llm` retries once on
invalid JSON, then degrades to `not_financial` at confidence `0.0` rather than
propagating a bad classification. `extract_row` runs the parsed result through
`validate_extraction`, a confidence threshold, *and* a sanity bound on
`doc_date` against the email's own received date — three independent checks,
any one of which routes to a `review` queue instead of the ledger. The design
rule visible across both is: **an LLM output is a candidate, not a fact, until
something deterministic has checked it** — and the something is always
specific to what could plausibly go wrong (bad JSON, low confidence, an
implausible date), not a generic try/except.

### 3.3 Cost Capture as a Design Commitment, Not an Add-On

`billextract.pricing` and the `cost_usd` field threaded through
`extract_row` → `ledger.store` were not part of the original P0 scope — they
landed in the final commit of the measured range
(`feat(expenses): capture AI extraction cost per ledger entry`, `aaa7fb3`).
That it arrived as a clean, fully-tested, single-purpose addition (its own
`pricing.py`, its own `test_cost_capture.py` and `test_ai_cost.py`, no changes
required to the schema's existing columns beyond adding the cost ones) is
itself evidence of the artifact-boundary design in §3.1 paying off: adding a
field that flows through every stage from extraction to reporting required no
stage to know about another stage's internals, only that the JSONL/SQLite
contract had grown one more optional key.

### 3.4 Recovery Paths Designed Before They Were Needed, Then Actually Used

`fetch.py`'s `MailHistoryExpiredError` handling — catch the expiry, resync via
the same bounded-lookback query a first run uses, log what happened, continue
— was written as part of the original design (the query-bounding logic and
the historyId cursor are both present from early commits), not bolted on
after a failure. The critique's operations section records that this exact
path fired in production on 2026-07-12. The design-then-verify order here
(build the recovery path from the cursor's known retention limit, rather than
wait for a production incident to reveal the need) is the pattern worth
naming: **the failure mode was anticipated from the mechanism's documented
limits (Gmail's ~1-week history retention), not discovered by an outage.**

## 4. Architecture Pattern

### 4.1 Five Packages, One Script

```
┌────────────┐  JSONL   ┌──────────────┐  JSONL   ┌─────────────┐
│ mailfetch  │─────────▶│ billclassify │─────────▶│ billextract │
│ (Gmail API)│          │ (heuristic + │          │ (LLM extract│
│            │          │  LLM fallback)│          │ + schema gate)│
└────────────┘          └──────────────┘          └──────┬──────┘
                                                          │ JSONL
                                                          ▼
┌───────────────┐  SQLite  ┌────────┐
│ expensereport │◀─────────│ ledger │◀── idempotent upsert, dedup-suspect flag
│ (Markdown)    │          │        │
└───────────────┘          └────┬───┘
        │                       │
        ▼                       ▼
┌───────────────┐        (SQLite is also the
│  expenseweb   │◀───────  input to expenseweb's
│ (HTML render) │        self-contained dashboard)
└───────────────┘

run_pipeline.sh sequences all five stages by shelling to `python3 -m <pkg>`;
a lockfile serializes cron invocations; state (the Gmail historyId) advances
only after mailfetch succeeds.
```

### 4.2 The Heuristic/LLM Split as a Cost-and-Determinism Lever

`classify_heuristic` resolves anything from a known biller or a subject
keyword match without touching the LLM at all; only genuinely ambiguous mail
reaches `classify_llm`. Architecturally this is a cache in front of an
expensive, non-deterministic call — but unlike a typical cache it is keyed on
*domain knowledge* (a configured `known_billers` list) rather than on prior
LLM output, so it never needs invalidation and never risks serving a stale
answer.

### 4.3 The Ledger as the System's Only Stateful Store

Every other stage is a pure transform over its input file. `LedgerStore` is
the one component with a real lifecycle (a SQLite connection, a transaction
per run) and the one place idempotency has to be engineered rather than
inherited for free from "just re-read the file." Concentrating state in a
single component with `message_id UNIQUE` as its idempotency key means every
other stage can be rerun, replayed, or debugged by just re-invoking it against
the same JSONL — a property directly inherited from §3.1's on-disk-artifact
coupling.

## 5. Development Pattern (from git history)

### 5.1 A Merge-Then-Harden Cadence

The 36-commit history on `origin/master` shows a clear shape: a P0 merge on
2026-07-06 (the plan's Tasks 0–9), followed by a sequence of paired
`fix:`/`feat:` commits, each addressing one specific, named production-shaped
bug, each merged individually rather than batched:

```
fix: real mailbox dry-run boundary bugs
fix(mailfetch): apply lookback_days to the first-run query
fix(billextract): sanity-bound doc_date against email received date
ops(cron): daily cron wrapper for run_pipeline.sh
ops(cron): monthly report wrapper (previous completed month)
feat(expenseweb): self-contained HTML dashboard + cron regen
feat(expenseweb): live search/filter box on the dashboard
fix: model refunds/credits so they net against charges
feat: split Anthropic subscription vs API usage by amount rule
fix(mailfetch): self-heal on deleted messages and expired history cursor
feat(expenses): capture AI extraction cost per ledger entry
```

This is a **harden-against-reality** cadence: the fixes above are not
speculative robustness, they are the exact bug classes a real mailbox surfaces
(a first run that would have pulled everything; a doc_date the LLM lifted from
the wrong part of an email; a refund that looked like a duplicate charge; a
cursor that outlived Gmail's retention window; a deleted message between list
and fetch). Each one landed with its own regression test in the same commit
grouping, per the critique's test-coverage findings.

### 5.2 Every Merge Commit Names Its Own Fix Category

The commit messages consistently use a `type(scope): specific claim` shape
(`fix(mailfetch): self-heal on deleted messages and expired history cursor`,
not `fix: bugs`), and every `fix:` commit's message states the *symptom* it
addresses, not just the code area — a pattern that makes `git log --oneline`
alone a fairly complete changelog substitute, which is notable given the
critique also flags the *absence* of an actual CHANGELOG file.

### 5.3 Operational Wrapper Scripts Arrived as Their Own Commits

`ops(cron): daily cron wrapper for run_pipeline.sh` and
`ops(cron): monthly report wrapper` are separate, dedicated commits — cron
installation was not folded into the P0 merge as an afterthought, but treated
as its own deliverable with its own commit message, after the pipeline itself
had already been proven stage-by-stage. This mirrors §2.2's "prove cheap
things first, add cost/risk later" scoping instinct applied to the
*deployment* step rather than the code.

## 6. Key Decisions and Their Rationale

### Decision 1: Pipeline, not agent — the LLM never chooses control flow

**Why:** Financial data must be reproducible; an agent's control-flow choices
are not. Confining the LLM to two narrow, schema-gated transforms keeps "same
inputs → same ledger" true regardless of model variance.

**Trade-off:** ADR-0001 names it directly — artifact I/O between stages and
some field duplication across JSONL lines, versus the tighter coupling a
single agentic loop would have.

### Decision 2: Gmail API + OAuth over IMAP + app password

**Why:** ADR-0002 — richer server-side query support (`category:`, `label:`,
`after:`) and OAuth over a static app password.

**Trade-off:** Heavier dependency footprint and an interactive consent flow;
`mailfetch` is no longer stdlib-only, unlike atri-sangam's air-gap-first core.
Appropriate here because this tool's entire premise requires network access
to a specific Google-hosted mailbox — there is no air-gapped deployment mode
to protect.

### Decision 3: `pdfminer.six` over shelling to poppler's `pdftotext`

**Why:** ADR-0002 — pure-Python, `pip`-installable, no system binary
prerequisite. Consistent with keeping every stage installable via
`pip install -e packages/<name>` alone.

**Trade-off:** `pdfminer.six`'s extraction quality and speed versus a
battle-tested C library; accepted because PDF text is explicitly a
body-insufficient fallback (`extract._context` only reaches for it when the
email body itself is under 40 characters), not the primary extraction path.

### Decision 4: Money as `Decimal`-as-`TEXT`; dedup by `message_id` + `(vendor, invoice_number, type)`

**Why:** ADR-0003 — no float ever touches an amount (test-enforced), and the
idempotency key is a real Gmail identity (`message_id`) rather than a derived
one, so a rerun can never double-count a message it already ledgered. The
secondary duplicate-suspect check is scoped by `entry_type` specifically so a
refund's legitimate reuse of its charge's invoice number does not read as a
duplicate charge.

**Trade-off:** ADR-0003 names it — report-time arithmetic must reconstruct
`Decimal` from `TEXT`, and cross-currency values are never summed (a
correctness choice, not a missing feature).

### Decision 5: Name the two untested boundaries in the plan, not discover them in a coverage report

**Why:** Mocking a full Google API client or a real PDF-parsing library
end-to-end buys little confidence relative to its cost, and both boundaries
are thin enough (a fixed `list_ids`/`get_message` interface; a
try/except-and-raise wrapper around `pdfminer.high_level.extract_text`) that
the risk of a silent regression is low relative to the risk in the logic
around them, which *is* fully tested.

**Trade-off:** Both boundaries' real behavior is validated only by running
against reality — which, per the critique, is now happening daily rather than
in a one-time dry run, closing the gap this trade-off originally accepted
faster than the plan anticipated.

### Decision 6: Cost capture added as a late, additive feature rather than designed in from Task 0

**Why:** The on-disk-artifact coupling (§3.1) meant a new field could be
threaded through extraction → ledger → report without any stage needing to
know about another's internals — so there was no structural cost to deferring
it until token-usage tracking was actually wanted.

**Trade-off:** Ledger rows written before `aaa7fb3` have no cost data (the
schema addition is additive, not backfilled) — acceptable for a tool whose
primary purpose is the expense record itself, not the cost-of-running-itself
metric, but worth knowing before treating the cost column as complete history.

## 7. What This Pattern Teaches

### Lesson 1 — "Pipeline, not agent" is a scoping decision that pays for itself at the LLM-exit gate

The single design choice with the most downstream effect is confining the LLM
to two stages and putting a deterministic gate at the exit of each. Every
hardening commit in §5.1 (doc_date sanity, refund handling, low-confidence
routing) is a *gate*, not a prompt tweak — the project's instinct when a real
mailbox produced a wrong answer was to add a check, not to reword the system
prompt and hope. That instinct is only available because the architecture
already drew the line between "LLM produces a candidate" and "code decides
whether to trust it."

### Lesson 2 — Naming an untested boundary in the plan, before code exists, is stronger than discovering it later

`gmail_client.py`'s "no unit test, exercised only against reality" was written
into the plan document before Task 5 existed. Contrast the more common
failure mode where a coverage report reveals a gap after the fact and the
team has to reconstruct why it's there. Naming the gap at design time meant
the interface the untested code had to match (`FakeGmail`'s shape) was
specified in the same breath as the decision to leave it untested — the gap
and its safety net were designed together.

### Lesson 3 — On-disk artifacts as inter-stage contracts make late additions (nearly) free

Cost capture, the amount-based category split, and the dashboard's live
search box all landed as clean, small, fully-tested commits well after P0.
None required touching more than one or two packages, because each package's
contract with its neighbors is "a JSONL/SQLite shape with these keys," not
"an imported function signature." The lesson generalizes past this project:
the looser the coupling between stages, the cheaper a feature that only
*adds* a field turns out to be, regardless of how deep in the pipeline it
lands.

### Lesson 4 — A recovery path designed from a documented external limit, not from an incident, is the higher-leverage move

The Gmail history-retention resync existed in the code before it was needed,
derived from a fact about the *platform* (history entries expire after
roughly a week) rather than from watching a real failure happen first. When
the limit was actually hit in production on 2026-07-12, the system did exactly
what the design anticipated. The teachable move is: when integrating against
a third-party API, read its documented limits for what *will* eventually
happen, and build the recovery path from that reading — not from the first
outage report.

---

*Development-pattern analysis grounded in a full read of `packages/**`,
`docs/adr/**`, `docs/superpowers/plans/**`, `README.md`, `run_pipeline.sh`, and
`scripts/**`, plus `git log origin/master` (36 commits, 2026-07-06 to
2026-08-01) and the live runtime state on the machine that runs the daily
cron. Consistent with the companion [wegofwd-expenses-critique.md](wegofwd-expenses-critique.md)
(v1.0). Cost-of-time-and-money analysis is maintained privately.*
