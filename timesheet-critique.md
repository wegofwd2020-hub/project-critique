# Timesheet — Code Review & Critique

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

**Reviewed:** 2026-09-03 (v1.0 — first review, against `origin/main` at `dd7d888`)
**Repo:** `wegofwd2020-hub/wegofwd-hub` (private) — **`timesheet` is a Django app inside the
wegofwd-hub repo, not a standalone product repo.** It shares the hub's settings, URL root,
and test runner with `portal` and the hub's other tiles.
**Phase:** Shipped, merged to `main`, live at `127.0.0.1:8088/timesheet/` via the hub's
systemd user service. First interactive first-party app in wegofwd-hub (everything else in
the hub is a rendered-file or link tile).
**Scope:** Testers'/contractors' time-by-project tracking (hours × a per-entry USD rate) and
bank-payment tracking (with transfer fees), rolled up into per-tester running balance
(earned − paid) and per-project cost, with a monthly drill-down, CSV export for the books,
and a hub tile. Local-only, `127.0.0.1`, no authentication by design.
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [timesheet-development-pattern.md](timesheet-development-pattern.md) ·
[timesheet-practices.md](timesheet-practices.md)

---

## Executive Summary

Timesheet is a small, well-scoped Django app — 309 lines of production Python, 311 lines of
tests, 94 lines of templates — built in a single ~1h49m session (spec → plan → 13 commits →
merge, 2026-09-01 08:04–09:53) as two chained SDD passes: an 8-task base build merged at
`6f747c2`, then a same-day drill-down feature merged at `dd7d888`. The money model is the
thing to get right in an accounting tool, and it is right: `hours`/`rate_usd`/`amount_usd`
are all `Decimal`, never `float`; `TimeEntry.amount_usd` and `Payment.total_cost_usd` are
derived `@property` methods computed on read, never stored columns, so there is no column to
drift out of sync with its inputs. `summary.py` is a pure aggregation module with zero
Django HTTP surface, and `views.py` is thin — forms in, `summary_mod`/`export_mod` calls out,
render.

The one real correctness subtlety is that **the app computes the same "earned" quantity two
different ways, and they can disagree by a cent.** `TimeEntry.amount_usd` rounds
per-entry (`(hours * rate_usd).quantize(CENTS)`), which is also what the CSV export and the
drill-down's per-row `amount` use. The summary dashboard's `earned` field, by contrast, is a
single database `Sum(F("hours") * F("rate_usd"))` — an unrounded sum of unrounded products,
quantized once at the end. Round-many-then-sum and sum-then-round-once are both defensible
roundings, but they are not the same function, and nothing in the code or docs says a
reconciler should expect them to foot exactly (§4).

Test honesty holds up: 39 tests across 4 files (not the "~52" figure a prior planning note
estimated — see the Snapshot note), and they assert real computed values, not response-code
smoke checks — `Decimal("35.00")` from `hours=3.5 × rate=10`, `balance == earned - paid` from
a hand-built fixture, drill-down entries asserted by date/project/hours/amount. Thirteen of
the 27 view tests exist specifically to close 500-error vectors found and fixed across three
consecutive commits the same session (malformed month, non-numeric tester id, oversized
tester id, unicode digits that pass `isdigit()` but fail `int()`) — a real hardening arc, not
padding.

**No-auth-by-design** is defensible for what this actually is: `ALLOWED_HOSTS =
["127.0.0.1", "localhost"]` at the hub level, no external port forwarded, single operator.
It is not defensible in the abstract — there is no session, no user field on any row, and no
CSRF-adjacent reasoning beyond "nothing routes here from outside `127.0.0.1`." That is a
property of the hub's deployment, not of the timesheet app, so it is only as safe as the hub
stays un-exposed (§5).

**Verdict:** A tight, honestly-scoped internal accounting tool with the one design decision
that actually matters (money as Decimal, derived not stored) done correctly, one real and
underdocumented reconciliation caveat, and a no-auth posture that is fine today and worth a
one-line contract if the hub's exposure ever changes.

## Snapshot

| Dimension | Value |
|---|---|
| Production Python LOC | **309** (`models.py` 50, `summary.py` 76, `views.py` 103, `forms.py` 23, `export.py` 26, `urls.py` 18, `admin.py` 7, `apps.py` 6) |
| Template LOC | 94 (6 files: base, form, summary, time_list, pay_list, tester_list) |
| Test LOC | 311 across 4 files |
| Tests | **39**, all in `timesheet/tests/` (4 models, 5 summary, 27 views, 3 export) |
| Hub-wide tests (timesheet + portal + tiles/dashboard/archive/landing) | **56** |
| Models | 3 — `Tester`, `TimeEntry`, `Payment` |
| Derived (never-stored) money fields | `TimeEntry.amount_usd`, `Payment.total_cost_usd` — both `@property` |
| FK delete behavior | `PROTECT` on `Tester` from both `TimeEntry` and `Payment` |
| Commits | 13 on the `timesheet/` path, 15 touching the feature incl. spec/plan/tile, 2026-09-01 08:04–09:53 (1h49m, single session, two merges) |
| Dependencies added | **0** — stdlib + Django + the hub's existing stack |
| Auth | **None by design** — local-only, `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]` at the hub level |
| CSRF | Django's default protection is active on every POST form (`{% csrf_token %}` present in `form.html` and the inline delete forms) |
| Lint/type gate | None found in this app or the hub CI beyond `manage.py test` |

**Note on the "~52 tests" figure.** An earlier planning note for this product estimated
"52/52 tests … 8 tasks." Measured directly against `origin/main` at `dd7d888`, the timesheet
app carries **39** test methods (the hub-wide total, including `portal` and the
dashboard/archive/landing/tiles tests, is **56**, matching the drill-down merge commit's own
"56/56" claim). Treat the measured number as authoritative; the estimate was stale.

## 1. Architecture

### Strengths
- ✅ **Money and hours are `Decimal` end to end.** Every quantity that is ever added, multiplied, or displayed as currency — `hours`, `rate_usd`, `amount_usd`, `transfer_charge_usd`, `total_cost_usd`, `earned`, `paid`, `fees`, `balance` — is a `DecimalField` or a `Decimal` computed from one. No `float` appears anywhere in the money path.
- ✅ **Derived properties instead of stored, denormalized columns.** `TimeEntry.amount_usd` and `Payment.total_cost_usd` are computed on access from `hours`/`rate_usd` and `amount_usd`/`transfer_charge_usd` respectively (`models.py`). There is no `amount_usd` column to fall out of sync with an edited `hours` or `rate_usd` — editing a `TimeEntry` via `time_edit` cannot leave a stale total anywhere, because no total is ever stored.
- ✅ **`summary.py` is genuinely pure.** `per_tester()` and `per_project()` take no request, return plain dicts/lists, and are unit-tested directly (`test_summary.py`) with zero Django test-client overhead. `_months()` is a private pure helper doing the same grouping logic for both call sites — one grouping algorithm, two consumers, not two copies.
- ✅ **Views are thin and share code via small dispatch helpers.** `_add`, `_edit`, `_delete`, and `_filter` are the entire non-trivial logic in `views.py`; `time_add`/`pay_add`/`time_edit`/`time_delete`/`pay_edit`/`pay_delete` are one-line wrappers around them. Adding a fourth model (there won't be one soon, but the shape is proven) would cost four one-liners, not four new view bodies.

### Gaps & Risks
- ⚠️ **`_filter`'s project-filter guard is silent, not explicit.** `qs.filter(project=proj) if hasattr(qs.model, "project") else qs` (`views.py`) exists so that a `?project=` querystring on `pay_list` (Payment has no `project` field) degrades to a no-op instead of raising `FieldError`. It works, and it is covered indirectly by the "unknown filters degrade gracefully" test class, but the mechanism — duck-typing on `hasattr(qs.model, ...)` — reads as an accident of code reuse between `time_list` and `pay_list` rather than an intentional API. A comment at the `hasattr` line, or two thin call sites instead of one shared `_filter`, would make the intent explicit rather than inferable.
- ⚠️ **`_delete` has no confirmation step.** `time_delete`/`pay_delete` delete unconditionally on any POST to the URL (`_delete`, `views.py`) — there is no "are you sure" page. Low-stakes for a single-operator local tool where CSRF already limits who can POST, but a mis-clicked "del" button (see the inline one-button delete forms in `time_list.html`/`pay_list.html`) is unrecoverable; there is no soft-delete or undo anywhere in the model.

## 2. Code Quality

### Strengths
- ✅ **`export.py`'s CSV-injection guard is a small, correctly-scoped fix.** `_csv_safe()` prefixes a leading `=`, `+`, `-`, `@`, tab, or CR with a single quote, covering the OWASP formula-injection character set, and is applied uniformly to every field written to either CSV (`time_rows`/`pay_rows`). It was added in its own commit (`2d7f002`) with a dedicated regression test (`test_csv_injection_neutralized`) rather than folded silently into the export feature commit — an auditable fix.
- ✅ **Zero new third-party dependencies.** The whole feature is stdlib + Django + the hub's existing `requirements.txt`.
- ✅ **Validators live on the model, not scattered across forms/views.** `MinValueValidator(Decimal("0.01"))` on `hours` and `Payment.amount_usd`, `MinValueValidator(Decimal("0"))` on `rate_usd` and `transfer_charge_usd` (`models.py`) — one place enforces "hours/payment must be positive, rate/fee may be zero," and both the admin site and every `ModelForm` inherit it for free.
- ✅ **`on_delete=PROTECT` on both FKs to `Tester`.** Deleting a tester who has time entries or payments raises `ProtectedError` rather than cascading data loss or silently orphaning rows — the right default for an accounting record.

### Gaps & Risks
- ⚠️ **`hub/settings.py` runs with `DEBUG = True`** (verified on `origin/main`) on the same settings module `timesheet` is served from. Bounded by `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]` today, but `DEBUG = True` means any unhandled exception in `timesheet`'s views renders a full traceback (including local variables and the SQL that ran) rather than a generic error page. This is a hub-wide setting, not a timesheet-specific one, but it is part of the wiring this app is served through and worth a line in the hub's own practices doc if one exists.
- ⚠️ **No lint or type gate anywhere in the app or its CI wiring** (`manage.py test` is the only quality gate found). The code reads clean — consistent naming, no dead imports, no bare `except` — but nothing enforces that going forward.

## 3. Test Coverage — Honesty Check

### Strengths
- ✅ **Assertions are real, not smoke.** `test_time_amount_is_hours_times_rate` asserts `Decimal("35.00")` from `3.50 × 10.00`; `test_per_tester_balance_and_fees` builds a two-entry, one-payment fixture by hand and asserts `hours`, `earned`, `paid`, `fees`, and `balance` each against a hand-computed value; the drill-down tests assert exact month keys, chronological ordering, and per-row date/project/hours/amount.
- ✅ **The 500-hardening tests document a real incident, not hypothetical coverage.** `test_list_graceful_on_year_zero_month` ("`month=0000-00`") and `test_list_graceful_on_huge_tester_id` ("`tester=999...9` × 30 digits") carry inline comments — `# was 500: date year 0 out of range` / `# was 500: int too large for SQLite` — that read as regression tests for bugs actually hit, across the three consecutive `fix(timesheet):` commits (`8fe7e46`, `60ef284`, `9007c01`) in the session's own history. `test_list_graceful_on_unicode_digit_tester` closes a genuinely subtle Python gotcha: `"²".isdigit()` is `True` but `int("²")` raises `ValueError` — the fix (`9007c01`) switched the guard to `str.isdecimal()`.
- ✅ **CSV injection is tested against the exact payload class it defends against** — `project="=cmd()"`, `description="=SUM(A1:A2)"` — and the test asserts both the quote-prefix and the absence of the raw unguarded string, not just "no exception."
- ✅ **Empty-state and zero-row paths are covered** (`SummaryPageEmptyTests.test_summary_renders_with_empty_db`), which is exactly the state a freshly-provisioned instance starts in.

### Gaps & Risks
- ⚠️ **The round-after-sum vs. round-per-entry discrepancy (§4) has no test asserting the two `earned` figures can differ.** Every fixture in `test_summary.py` uses rates and hours (`2×10`, `3×20`) that happen to multiply to exact cents, so the summary's `Sum(hours × rate)` path and `TimeEntry.amount_usd`'s per-entry path always agree in the test suite. A fixture with e.g. three entries of `1.115h × $10.005` (or any hours/rate pair whose product needs rounding) would surface the drift and pin the current behavior as intentional rather than untested.
- ⚠️ **No test exercises `Tester` deletion against `PROTECT`.** The FK `on_delete=PROTECT` behavior — arguably the one piece of referential-integrity logic in the app — has no `assertRaises(ProtectedError)` test anywhere in `test_models.py` or `test_views.py`.
- ⚠️ **`tester_list`/`tester_add`/`tester_edit` have thinner coverage than the time/payment CRUD paths** — no test for editing a tester's `active` flag off, and no test that an inactive tester still appears (or doesn't) in the `time_add` datalist or filter dropdowns.

## 4. Correctness — The Two-Ways-to-Compute-"Earned" Gotcha

This is the one design subtlety worth a dedicated section rather than a bullet.

**The two computations.**
- `TimeEntry.amount_usd` (a model `@property`, used by the CSV export and the drill-down's
  per-row `amount`): `(self.hours * self.rate_usd).quantize(CENTS)` — **rounds after every
  individual multiplication.**
- `summary.per_tester()`/`per_project()`'s `earned` field: a single Django ORM
  `Sum(F("hours") * F("rate_usd"))` aggregate — the database sums the raw
  `hours × rate_usd` products **before** any rounding, and the result is `.quantize(CENTS)`
  exactly once, at the end.

Both are standard, defensible ways to compute an aggregate over money — "round each line
item, then add the line items" and "add first, round the total" are both used in real
accounting systems, and they agree whenever every `hours × rate` product already lands on an
exact cent (which is the common case: whole or half hours against round dollar rates). They
can disagree by a cent whenever a product needs rounding and the rounding direction happens
to differ across entries — e.g. several entries each rounding fractionally up individually,
where the unrounded sum rounds down once. `summary._months()`'s per-month `earned` uses the
**same round-after-sum method** as the top-level figure (so a tester's month subtotals foot
exactly to their yearly total), but the per-row `amount` inside each month's drill-down uses
the **per-entry** method — meaning a careful reader who sums the visible per-row `amount`
values in a drill-down and compares to that same month's displayed `earned` could, in an
adversarial-rounding fixture, see the two not quite agree, in the same view.

**Why this matters here specifically.** Timesheet is an accounting tool whose whole purpose
is "does the CSV export foot to the dashboard." The CSV (`export.py`) uses the per-entry
method (`f"{e.amount_usd}"`); the dashboard's headline `earned` uses the sum-then-round
method. For most real rate/hours combinations they will match to the cent, but a bookkeeper
who has been burned by a one-cent reconciliation difference before will ask why, and today
there is no comment anywhere in `summary.py` or the README-equivalent explaining that the two
paths use different rounding strategies (the `_months()` docstring notes it applies "the same
round-after-sum method as the top-level Earned column" — correct and helpful — but does not
mention that the CSV/per-entry figure is the *other* method).

**Disposition:** not a bug — both roundings are individually correct and the discrepancy, if
it ever occurs, is at most a cent per tester per period — but it is an **underdocumented
reconciliation caveat** that should be one sentence in the summary template or a code
comment, so a future maintainer (or the operator doing the books) does not spend time
debugging a "discrepancy" that is actually two valid rounding conventions.

### Other correctness notes
- ✅ **Filter hardening (§3) closes a real class of bug.** All four vectors found (malformed month string, non-numeric tester id, oversized tester id overflowing SQLite's integer range, Unicode digits that pass `isdigit()` but fail `int()`) are now guarded in `_filter` and `_MONTH_RE`, each with a regression test.
- ✅ **CSV formula-injection guard is correctly scoped** to the OWASP-documented trigger character set and applied to every exported field uniformly, including the free-text `project`/`description`/`note` fields that a spreadsheet would actually interpret as formulas.

## 5. Security & the No-Auth-by-Design Decision

### Strengths
- ✅ **Consistent with the hub's stated posture.** `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]` at the hub-settings level, no port forwarded externally, single operator — the same posture every other hub tile assumes.
- ✅ **CSRF protection is on, not disabled.** Every mutating form (`add`, `edit`, and the inline one-button `delete` forms in the list templates) carries `{% csrf_token %}`. Not a redundant control given no-auth, but real defense against a same-origin drive-by if the operator's own browser ever renders untrusted HTML pointed at `127.0.0.1` — cheap insurance that was not skipped just because auth was skipped.
- ✅ **Django's autoescape protects the free-text fields.** `project`, `work_type`, `description`, `note`, and `reference` are all free-text `CharField`/`TextField` rendered with `{{ }}` (not `|safe`) in every template, so a tester or the operator typing `<script>` into a project name renders as inert text, not markup — a real mitigation even though there is no authentication boundary for it to protect.

### Gaps & Risks
- ⚠️ **No authorization model exists at any layer.** No session, no user field on `Tester`/`TimeEntry`/`Payment`, no per-row ownership — anyone who can reach `127.0.0.1:8088/timesheet/` can read, edit, or delete any row, including another tester's rate and payment history. This is fine for the stated single-operator/local posture and is explicitly out of scope in the design doc (`docs/superpowers/specs/2026-09-01-testers-timesheet-design.md`, §10: "authentication/multi-user … deferred"), but the safety of the whole app rests entirely on the hub never being exposed beyond `127.0.0.1` — a property of `hub/settings.py` and the systemd unit's bind address, not of anything in `timesheet/`.
- ⚠️ **The decision is undocumented at the point of risk.** Nothing in `timesheet/` itself — no comment, no README section — states the no-auth assumption or what would need to change if the hub were ever bound to a non-loopback address (e.g., over the Tailscale link the hub's own memory notes some other tools use). A one-line comment near `views.py`'s top, or a short note in the design doc's "out of scope," would turn an implicit assumption load-bearing across the whole app into an explicit, greppable one.

## 6. Documentation

### Strengths
- ✅ **A real design doc and implementation plan exist and match the shipped code.** `docs/superpowers/specs/2026-09-01-testers-timesheet-design.md` and `docs/superpowers/plans/2026-09-01-timesheet.md` describe exactly the models, summary logic, URLs, and CSV columns that exist on `origin/main` — no drift between the plan and the artifact, because both were committed the same session as the code they describe.
- ✅ **Money-model rationale is stated up front in the design doc** ("Money + hours are `DecimalField` (never float — accounting-safe)"; "`amount_usd` = property … derived, never stored — no drift") — the two decisions this review calls out as the app's real strengths were explicit design intent, not accidents of Django defaults.
- ✅ **`_months()`'s docstring explains its own rounding choice** ("Earned uses the same round-after-sum method as the top-level Earned column, so month subtotals foot to the tester/project total") — genuinely useful in-code documentation of a subtlety, though it stops short of naming the *other* method used elsewhere (§4).

### Gaps & Risks
- ⚠️ **No user-facing documentation of the reconciliation caveat (§4)** anywhere a bookkeeper doing the books would see it — not in the summary template, not in the CSV export, not in a README.
- ⚠️ **The design doc's "Out of scope (v2+)" list is the only place the no-auth decision is written down**, and it is phrased as a deferred feature ("authentication/multi-user … deferred") rather than a stated current-risk assumption (§5).
- ⚠️ **No standalone README for the app** — reasonable for an app this size living inside a larger repo's docs tree, but a newcomer to `wegofwd-hub` has to find the superpowers spec/plan docs to learn what `timesheet/` does; there is no `timesheet/README.md` or docstring at the top of `views.py`/`models.py` doing that job.

## Priority Actions

1. ⚠️ **Document the earned-figure reconciliation caveat (§4)** — one comment in `summary.py` near the `earned_sum` aggregate, and/or one sentence on the summary template, stating that the dashboard's per-tester/per-project `earned` and the CSV/drill-down per-entry `amount_usd` use different (both valid) rounding conventions and can differ by up to a cent per row when a product doesn't land on an exact cent.
2. ⚠️ **Add a fixture that actually exercises rounding disagreement** — an `hours`/`rate_usd` pair whose product needs rounding, asserted against both the summary `earned` and the sum of per-entry `amount_usd` values, to pin current behavior with a test rather than leave it implicit.
3. ⚠️ **State the no-auth assumption where the risk lives**, not only in the "out of scope" roadmap list — a short comment near `views.py`'s top or `hub/settings.py`'s `ALLOWED_HOSTS` line, naming what would need to change (auth, per-row ownership) before this app could safely be exposed beyond `127.0.0.1`.
4. ⚠️ **Add a `ProtectedError` test for `Tester` deletion** — the one referential-integrity guarantee in the model layer currently has no regression test.
5. ⚠️ **Add a lint/type gate** (ruff at minimum) to the hub's CI, covering `timesheet/` along with the rest of the repo — currently `manage.py test` is the only automated check.

---

*Reviewed against `wegofwd-hub`'s `origin/main` at `dd7d888` (2026-09-01), grounded in a full
read of `timesheet/models.py`, `summary.py`, `views.py`, `forms.py`, `export.py`, `urls.py`,
`admin.py`, `apps.py`, all four template files, all four test files, `hub/settings.py`,
`hub/urls.py`, `portal/tiles.py`, and the app's own spec/plan docs under
`docs/superpowers/`. Test counts and LOC are measured directly from `git show
origin/main:<path>` output, not run locally (no Django install in the review environment).
Cost-of-time-and-money analysis is maintained privately in `wegofwd-private-docs`.*
