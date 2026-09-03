# Timesheet — Scoping, Design, Architecture & Development Pattern

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/wegofwd-hub` |
| Branch | `main` |
| Git commit | `dd7d888` (as of 2026-09-01) |
| Product version | —  (commit-based; no release version) |
| Doc updated | 2026-09-03 |
| Last deployed | local-only — live at 127.0.0.1:8088/timesheet/ via the wegofwd-hub systemd user service; not externally deployed |
<!-- doc-meta:end -->

**Document type:** Development-pattern analysis
**Scope:** How a small internal accounting app was scoped, designed, and built inside an
existing multi-tenant Django project (`wegofwd-hub`) via a chained, same-day SDD cycle —
not a security or correctness assessment (see
[timesheet-critique.md](timesheet-critique.md) for that).
**Repo note:** `timesheet` is a Django app living inside the `wegofwd2020-hub/wegofwd-hub`
repo, not its own repository. It shares the hub's `settings.py`, root `urls.py`, virtualenv,
and `manage.py test` runner with `portal` (the hub's landing page / tile registry) and every
other tile.
**Period:** 2026-09-01, 08:04–09:53 (1h49m), two chained feature branches merged the same
day: `feat/timesheet` (base app, merged `6f747c2`) → `feat/timesheet-drilldown` (monthly
drill-down, merged `dd7d888`).
**Author:** WeGoFwd2020 / Claude (Anthropic)
**Related:** [timesheet-critique.md](timesheet-critique.md) · [timesheet-practices.md](timesheet-practices.md)

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [Scoping Pattern](#2-scoping-pattern)
3. [Design Pattern](#3-design-pattern)
4. [Architecture Pattern](#4-architecture-pattern)
5. [Development Pattern — Commit Cadence](#5-development-pattern--commit-cadence)
6. [Key Decisions and Their Rationale](#6-key-decisions-and-their-rationale)
7. [What This Pattern Teaches](#7-what-this-pattern-teaches)

---

## 1. The Problem Being Solved

Testers and contractors (the design doc names one, "Venki," by way of example) log time
against WeGoFwd products. Each submission is a date, an hour count, and what was done. The
operator sets a **USD rate per entry, keyed by work type** — manual QA might be priced
differently from automation work — so `earned = hours × rate` is different per line, not a
fixed per-tester rate. Payments go out by bank transfer in USD, and bank transfers carry a
fee that is itself money the org spends and needs to track. The org needs three views on this
data for the books: time logged by project (what did this cost per product), money earned
vs. paid per person (who is owed what), and the transfer fees (a real cash-out line item),
all exportable to CSV for whatever accounting process consumes it downstream.

This is the hub's **first interactive first-party app** — every other tile in `wegofwd-hub`
either renders a pre-generated HTML file (`portfolio`, `doc-digest`, `expenses`, `local-watch`)
or links out to a federated service (`medtracker`). Timesheet is the first tile that is itself
a full CRUD Django app living inside the hub project, which is why the design doc frames the
hub-integration decision explicitly rather than assuming it (§2.1).

## 2. Scoping Pattern

### 2.1 Scope Anchored by "Where Does This App Live," Decided First

The very first locked decision in the design doc (`docs/superpowers/specs/2026-09-01-testers-timesheet-design.md`,
§2) is not a data-model question but a placement question: *"a tile + app inside
wegofwd-hub … this is the hub's first interactive first-party app; medtracker etc. stay
federated links."* Scoping the deployment shape before the schema is the move that lets
everything downstream (no auth, `127.0.0.1` posture, SQLite, reuse of the portal's look) fall
out as inherited constraints rather than separate decisions — the app doesn't choose its own
security posture, it inherits the hub's.

### 2.2 Money Modeling Scoped by "What's Derived vs. What's Stored," Not by Feature

The design doc's §3 draws the model boundary along a single axis: which quantities are
**inputs** (`hours`, `rate_usd`, `amount_usd` paid, `transfer_charge_usd`) and which are
**derived** (`amount_usd` earned per entry, `total_cost_usd` per payment, the running
balance). Only inputs get a column; every derived quantity is a Python `@property` or a
`summary.py` aggregate computed from inputs at read time. This is a scoping decision with a
direct testability and correctness payoff: there is no denormalized total anywhere in the
schema that a future edit path could forget to update.

### 2.3 Subtractive Scoping — An Explicit "Out of Scope (v2+)" List

Like `dronePrjs`'s ISA block and `atri-sangam`'s roadmap, the design doc closes with a named
list of what is *not* being built now (§10): linking a payment to specific time entries
(partial-payment reconciliation), pushing payments into the `wegofwd-expenses` ledger,
multi-currency, authentication/multi-user, invoices/PDF, an approval workflow. Each item is
named and left absent — there is no half-built "invoice" model or a `currency` field that is
always `"USD"` sitting unused. The "running balance = Σ earned − Σ payments" design (rather
than tracking which specific entries a payment settles) is the direct consequence of deferring
partial-payment reconciliation — a simpler, coarser model chosen because the finer one was
explicitly out of scope, not because the finer one wasn't considered.

### 2.4 The Drill-Down as a Deliberately Separate, Same-Day Second Pass

The monthly drill-down (`_months()` in `summary.py`, the `<details>` markup in
`summary.html`) was not part of the original 8-task plan — it landed as its own spec-free,
plan-free feature branch (`feat/timesheet-drilldown`) merged 16 minutes after the base app.
Scoping it as a second increment rather than a ninth task in the original plan kept the base
app's definition-of-done (§ Definition of Done in the plan doc) achievable and shippable on
its own; the drill-down was additive to an already-working, already-tested surface rather than
a blocking dependency of it.

## 3. Design Pattern

### 3.1 Decimal Everywhere, Two Rounding Conventions Left Implicit

Every money and hours field is a `DecimalField`; every derived quantity is computed in
`Decimal` arithmetic and `.quantize(Decimal("0.01"))`'d before display. This is the single
most load-bearing design choice in the app — accounting software built on `float` is a
recurring, well-known failure mode, and it was avoided from the first commit (`a2de107`,
"models … app registration"). What the design left implicit (see
[timesheet-critique.md §4](timesheet-critique.md#4-correctness--the-two-ways-to-compute-earned-gotcha)
for the full analysis) is that "derive, don't store" was applied at two different
granularities — per-entry in the model property, per-aggregate-then-once in the summary
module — without a stated rule for which granularity a given call site should use. Both
choices are individually defensible; the design doc doesn't name them as two choices.

### 3.2 Pure Aggregation Module, Zero HTTP Awareness

`summary.py` imports only `decimal`, Django's ORM aggregation primitives (`Sum`, `F`,
`DecimalField`, `Value`, `Coalesce`), and the three models. `per_tester()` and `per_project()`
take no `request` and return plain `dict`/`list` structures. This mirrors the same
pure-transformer instinct seen in `atri-sangam`'s collectors and `local_watch`'s rules
engine: put the part of the system with actual logic (grouping, summing, rounding) behind a
function signature a unit test can call directly, and leave the HTTP-shaped code (`views.py`)
to do nothing but glue.

### 3.3 Thin-View Dispatch Through Four Shared Helpers

Rather than eight near-identical `CreateView`/`UpdateView`/`DeleteView` subclasses (one per
model per operation), `views.py` factors the CRUD shape into four function-based helpers —
`_add(request, form_cls, title, datalists)`, `_edit(request, model, form_cls, pk, list_name)`,
`_delete(request, model, pk, list_name)`, `_filter(qs, request, date_field)` — and every
public view (`time_add`, `pay_add`, `tester_add`, `time_edit`, `pay_edit`, `tester_edit`,
`time_delete`, `pay_delete`, `time_list`, `pay_list`) is a one- or two-line call into one of
them. The design pattern is "parameterize the shape, not the model" — a fourth CRUD model
would cost roughly four one-liners, not four new view classes.

### 3.4 Filter Hardening as an Iterative, Test-Driven Loop Within One Session

`_filter()` and its `_MONTH_RE` guard were not designed defensively up front — they were
hardened across three consecutive `fix(timesheet):` commits (`8fe7e46`, `60ef284`, `9007c01`)
in the same session, each one closing a specific 500-producing input discovered by trying to
break the just-shipped filter: a malformed month string, a tester id that overflows SQLite's
integer range, and a Unicode digit character that passes `str.isdigit()` but fails `int()`.
This is the "write it, then attack it, then fix it, same session" pattern rather than
threat-modeling every input class before writing the first filter — a reasonable trade-off
for a `127.0.0.1`-only internal tool, and each fix shipped with its own regression test in the
same commit.

### 3.5 CSV Export as a Late, Separately-Committed Security Fix

The CSV export feature (`319c96a`) and its formula-injection guard (`2d7f002`) are two
separate commits three minutes apart, not one commit. The export shipped first without the
guard, then the guard was added as its own change with its own test
(`test_csv_injection_neutralized`). Splitting a feature and its security hardening into
separate, individually-revertible commits — rather than folding the fix silently into the
feature commit — is a small but real practice: a `git log` reader can see exactly which
commit introduced the guard and why, and `git bisect` on a future CSV regression has a clean
boundary.

## 4. Architecture Pattern

### 4.1 Three-Layer Stack, One Direction of Data Flow

```
┌──────────────────────────────────────────────────────────┐
│ Templates (base / form / summary / time_list / pay_list / │
│            tester_list) — Django template language only,  │
│            no client-side JS                               │
└──────────────────────────────────────────────────────────┘
                          ▲  context dicts
┌──────────────────────────────────────────────────────────┐
│ views.py — thin dispatch: _add / _edit / _delete / _filter │
│            forms.py — ModelForm × 3                        │
│            export.py — pure CSV row builders                │
└──────────────────────────────────────────────────────────┘
                          ▲  summary_mod.per_tester()/per_project()
┌──────────────────────────────────────────────────────────┐
│ summary.py — pure aggregation (querysets → dicts, no HTTP) │
└──────────────────────────────────────────────────────────┘
                          ▲  ORM queries
┌──────────────────────────────────────────────────────────┐
│ models.py — Tester / TimeEntry / Payment, Decimal fields,  │
│             @property amount_usd / total_cost_usd          │
└──────────────────────────────────────────────────────────┘
```

Each layer only calls the one below it — templates never touch models directly (always
through a view's context), `views.py` never reaches into `summary.py`'s internals (only its
two public functions), and `summary.py` never imports anything from `views.py` or
`export.py`. The layering is enforced by convention, not by package boundaries (everything is
one Django app, one Python package), but the import graph on `origin/main` respects it
exactly.

### 4.2 The Hub as the Outer Shell

`hub/urls.py` mounts `timesheet.urls` at `/timesheet/` ahead of `portal.urls`'s catch-all
include, and `portal/tiles.py` carries the single `{"slug": "timesheet", "kind": "link",
"target": "/timesheet/"}` entry that makes the app reachable from the landing page. This is
the same "one dict = one tile" extensibility seam the hub uses for every other product
(`expenses`, `local-watch`, `medtracker`) — timesheet is architecturally just another tile
that happens to be a full Django app rather than a rendered file, and the tile registry does
not need to know the difference.

### 4.3 Derived-Property Money as an Architectural Invariant

`amount_usd` and `total_cost_usd` being `@property` rather than stored fields is not just a
model-layer detail — it is the thing that lets `views.py`'s `_edit` helper stay generic.
Because `TimeEntryForm` and `PaymentForm` only ever write the *input* fields (`hours`,
`rate_usd`, `amount_usd` paid, `transfer_charge_usd`), a single generic `_edit()` can save any
of the three forms without any model-specific post-save recomputation step. If `amount_usd`
were a stored column, `_edit` would need a per-model "and now recompute the total" branch,
breaking the genericity §3.3 relies on.

### 4.4 Two Summary Consumers, One Grouping Function

`_months()` is called identically from `per_tester()` (grouping a tester's entries by month,
labeling each row by `project`) and `per_project()` (grouping a project's entries by month,
labeling each row by `tester`). The `label` parameter is the only branch point. This is a
small but real instance of factoring the *shape* of an aggregation (group-by-month,
subtotal, list dated rows) away from *which axis* it's being computed over — the same
instinct as `atri-sangam`'s channel-agnostic engine or `local_watch`'s per-machine collector
feeding one central aggregator.

## 5. Development Pattern — Commit Cadence

The full timeline, spec to final merge, all in one session on 2026-09-01:

```
08:04  spec: testers time & payments tracker (timesheet app)
08:08  plan: testers timesheet implementation (8 tasks, TDD, Django app)
08:20  feat: models (Tester/TimeEntry/Payment) + app registration          [T1]
08:39  feat: per-tester balance + per-project cost aggregation             [T2]
08:45  feat: add-time and add-payment forms + views                       [T3]
08:48  feat: datalists of prior project/work_type + reject-zero tests     [T3, extended]
08:53  feat: filterable lists + edit/delete for time & payments           [T4]
08:55  fix:  graceful list filters on malformed month/tester              [T4, hardening 1/3]
09:00  fix:  bound filter values to close residual 500 vectors            [T4, hardening 2/3]
09:05  fix:  use isdecimal so unicode-digit tester filter cannot 500      [T4, hardening 3/3]
09:07  feat: testers management page                                     [T5]
09:12  feat: CSV export for time entries and payments                    [T6]
09:15  fix:  neutralize CSV formula injection in export                  [T6, security fix]
09:20  feat: summary dashboard (per-tester balance + per-project cost)   [T7]
09:29  feat: add Testers & Payments tile linking to /timesheet/          [T8]
09:37  Merge feat/timesheet: testers time & payments tracker              ← v1 shipped
09:53  feat: monthly drill-down on per-tester & per-project reports       (2nd pass)
09:53  Merge feat/timesheet-drilldown: monthly drill-down on summary reports
```

**16 minutes of design before the first line of code** (08:04 spec → 08:20 first commit),
**1h17m of implementation** (08:20 → 09:37 merge) across 13 commits mapping cleanly to the
plan's 8 named tasks plus 3 unplanned hardening fixes and 1 unplanned security fix, then a
**16-minute second pass** for the drill-down feature. Three properties of this cadence are
worth naming:

- **Every `fix:` commit is a direct response to a `feat:` commit minutes earlier**, not a
  batch of hardening done at the end. The filter feature landed at 08:53; its three fixes
  landed at 08:55, 09:00, and 09:05 — each one probably found by immediately trying to break
  what had just shipped.
- **The plan's task boundaries and the commit boundaries match almost one-to-one** — T1
  through T8 each correspond to exactly one (or, for T3/T4, one plus its immediate hardening)
  commit, with no task spanning multiple unrelated commits and no commit spanning multiple
  tasks. The plan's own "Self-review notes" section pre-declares this mapping (T1–T8 against
  §3–§7 of the spec) before implementation starts.
- **The drill-down was not squeezed into the same merge.** Rather than reopening
  `feat/timesheet` to add one more task, it became its own branch and its own merge commit 16
  minutes later — keeping the first merge's history a clean record of exactly the 8-task plan
  it executed.

## 6. Key Decisions and Their Rationale

### Decision 1: Build inside `wegofwd-hub`, not as a standalone repo

**Why:** The hub already owns the `127.0.0.1`, no-auth, SQLite, systemd-service posture every
internal tool needs; timesheet only needs a URL prefix and a tile entry to inherit all of it.

**Trade-off:** Timesheet's tests, deploy state, and doc-meta stamping are now coupled to the
hub's — a hub-wide dependency bump or settings change can affect timesheet even though
nothing in `timesheet/` changed, and this critique suite's own tooling (`stamp_doc.py`) has
to special-case the `timesheet` doc-prefix to point at the `wegofwd-hub` repo rather than a
same-named one.

### Decision 2: Per-entry rate, not per-tester rate

**Why:** Different work types (manual QA vs. automation) are genuinely priced differently;
locking the rate at the `Tester` level would force a rate change every time a tester switched
task type, or force separate `Tester` rows per rate — both worse than a `rate_usd` field on
`TimeEntry` itself.

**Trade-off:** There is no single "what does this tester charge" answer anywhere in the UI —
the rate lives entirely in historical entries, so answering "what's Venki's current rate" is
a query over recent rows, not a field lookup.

### Decision 3: Running balance (Σ earned − Σ payments), not per-entry payment linkage

**Why:** Explicitly deferred to v2 in the design doc — linking a payment to the specific
entries it settles is real reconciliation work (partial payments, over/under-payment,
disputed entries) that the org didn't need on day one. A single running balance answers "who
is owed what, right now" with the simplest possible model.

**Trade-off:** There is no way to answer "was invoice #3 paid" — only "is this tester's
lifetime balance positive or negative." If a payment is meant to cover specific entries and
only partially does, that intent is lost; only the aggregate effect on the balance is
recorded.

### Decision 4: Derive `amount_usd`/`total_cost_usd`, never store them

**Why:** A stored total is a second source of truth that every edit path must remember to
recompute; a `@property` computed from the current `hours`/`rate_usd` (or
`amount_usd`/`transfer_charge_usd`) cannot drift, by construction — editing `hours` via
`time_edit` automatically changes what `amount_usd` reports on the very next read, with zero
extra code.

**Trade-off:** Every read pays a multiplication instead of a column lookup — irrelevant at
this data volume (a handful of testers, dozens to low-hundreds of entries), but a `Sum` over
a derived expression (as `summary.py` does) is materially more ORM-code than `Sum("stored_column")`
would be, and it's the reason two different rounding strategies exist at all (§3.1).

### Decision 5: Harden filters reactively, same session, rather than defensively up front

**Why:** For a `127.0.0.1`-only tool with one operator, the cost of "ship the filter, then
spend 15 minutes trying to break it" is lower than the cost of enumerating every malformed-
input class before writing the first version — and the three fixes that resulted
(`8fe7e46`, `60ef284`, `9007c01`) each shipped with its own regression test in the same
commit, so nothing was fixed without being pinned.

**Trade-off:** The three specific vectors closed (malformed month, oversized/non-numeric
tester id, Unicode-digit tester id) were the ones tried; there is no guarantee the reactive
process found every input class that could 500 the list views, only the ones probed.

### Decision 6: Ship the drill-down as a second, same-day pass rather than a ninth task

**Why:** Keeps the first merge's scope exactly the 8-task plan it was written against, so the
plan-to-commit mapping (§5) stays clean and the base app's own definition-of-done is testable
in isolation from the drill-down.

**Trade-off:** The drill-down has no spec or plan document of its own (unlike the base app) —
it is documented only by its commit message and its own docstring in `summary.py`'s
`_months()`. For a change this size that's a reasonable trade-off; it would not scale to a
larger unplanned addition.

## 7. What This Pattern Teaches

### Lesson 1 — Decide where a small app lives before deciding what it contains

Timesheet's design doc locks the hosting decision ("inside wegofwd-hub, inheriting its
posture") as decision #1, before the data model. Every subsequent "obvious" choice — no auth,
SQLite, `127.0.0.1`, reuse the portal's look — is then a consequence of that first decision
rather than a separately-justified one. For a small internal tool being added to an existing
platform, the placement decision usually *is* the security and operations decision; making it
first and explicitly means the app doesn't have to re-derive a posture the host already has.

### Lesson 2 — "Derive, don't store" needs one stated rounding rule, not per-call-site judgment

Deriving `amount_usd` from `hours × rate_usd` instead of storing it is unambiguously the right
call (Decision 4) — but the pattern has a sharp edge this codebase hits: derivation still
requires a rounding decision, and if that decision is made independently at each call site
(a model property here, an ORM aggregate there), two individually-correct roundings can
disagree on a value that reads as one number to a user. The lesson generalizes past money: any
time a "never store the derived value" rule is applied at more than one code site, the
*computation*, not just the *non-storage*, needs to be the single source of truth — either one
shared function both paths call, or one documented convention both paths follow.

### Lesson 3 — Split a feature from its security hardening into separate commits

CSV export and its formula-injection guard landing as two commits (§3.5), and each of the
three filter-hardening fixes landing as its own commit with its own test (§3.4), means a
`git log` reader — or a future incident investigation — can point at exactly the commit that
introduced a given protection and exactly the test that proves it. This costs nothing extra
at commit time and pays off the first time someone needs to know "when did we start guarding
against this."

### Lesson 4 — A same-day second pass is a legitimate way to scope an afterthought feature

The drill-down feature was not anticipated in the original plan, and rather than reopening the
already-merged branch or squeezing a ninth task into the plan retroactively, it shipped as its
own branch and merge 16 minutes later. For genuinely small, additive features on top of an
already-tested base, this keeps the historical record of "what was planned" and "what was
built to that plan" honest, at the cost of the addition itself getting a thinner paper trail
(no spec, no plan doc) than the base app did.

### Lesson 5 — Thin, parameterized view helpers scale better than per-model CRUD boilerplate for a small app

Four helper functions (`_add`, `_edit`, `_delete`, `_filter`) carrying the entire non-trivial
logic in `views.py`, with every public view reduced to a one-line call, is a pattern worth
copying for any small internal CRUD app with 2-4 similarly-shaped models: it keeps the
public view functions trivially readable and correct-by-inspection, and it means the one
place bugs can hide (the shared helper) gets exercised by every model's test suite, not just
one.

---

*Analysis grounded in a full read of `timesheet/` on `wegofwd-hub`'s `origin/main` at
`dd7d888`, its two commit ranges (`a2de107`..`6f747c2`, `da6e8d9`..`dd7d888`), and its spec/plan
docs under `docs/superpowers/`. Consistent with the companion
[timesheet-critique.md](timesheet-critique.md) (v1.0). Cost-of-time-and-money analysis is
maintained privately.*
