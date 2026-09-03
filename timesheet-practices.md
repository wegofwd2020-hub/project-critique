# Timesheet — Good Practices, Bad Practices & How to Improve

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

**Document type:** Engineering practices analysis
**Scope:** Django app (`timesheet/`) inside the `wegofwd-hub` repo — models, pure summary
aggregation, thin views, forms, CSV export, templates. **Not a standalone repo** — see
[timesheet-critique.md](timesheet-critique.md) for the repo-placement note.
**Period:** 2026-09-01 (v1.0 — first review, against `origin/main` at `dd7d888`)
**Related:** [timesheet-critique.md](timesheet-critique.md) · [timesheet-development-pattern.md](timesheet-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

---

## Table of Contents

1. Money & Data Modeling Practices
2. Architecture Practices
3. Security & Robustness Practices
4. Code Quality Practices
5. Testing Practices
6. Documentation Practices

---

## 1. Money & Data Modeling Practices

### ✅ Good — Decimal for every money and hours field, never float
`hours`, `rate_usd`, `amount_usd`, `transfer_charge_usd` are all `DecimalField` (`models.py`).
Every downstream computation — `TimeEntry.amount_usd`, `Payment.total_cost_usd`,
`summary.py`'s `earned`/`paid`/`fees`/`balance` — stays in `Decimal` all the way to
`.quantize(Decimal("0.01"))`. No `float` ever touches a money value in this app.

### ✅ Good — Derived totals are `@property`, never stored columns
`TimeEntry.amount_usd` and `Payment.total_cost_usd` are computed from their inputs on every
access, not written to the database. Editing `hours` or `rate_usd` via `time_edit` cannot
leave a stale total anywhere, because no total is ever persisted separately from the numbers
it's computed from.

### ⚠️ Bad — Two rounding conventions for the same logical quantity, undocumented as a pair
`TimeEntry.amount_usd` rounds after each individual `hours × rate_usd` multiplication;
`summary.py`'s `earned` aggregate sums the unrounded products across all of a tester's/
project's entries and rounds once at the end. Both are individually correct; nothing states
that they are two different conventions, so the CSV export (per-entry method) and the
dashboard's headline `earned` (sum-then-round method) can disagree by up to a cent on data
whose products don't land on exact cents.
🔧 **How to improve:** one comment near `summary.py`'s `earned_sum` aggregate and one sentence
on the summary template, naming both conventions and stating they can differ by a cent — see
[timesheet-critique.md §4](timesheet-critique.md#4-correctness--the-two-ways-to-compute-earned-gotcha)
for the full analysis and a proposed fixture to pin the behavior with a test.

### ✅ Good — `MinValueValidator` on the model, not scattered across forms
`hours ≥ 0.01`, `Payment.amount_usd ≥ 0.01`, `rate_usd ≥ 0`, `transfer_charge_usd ≥ 0`
(`models.py`) live once, on the field, and are inherited automatically by every `ModelForm`
and the Django admin — no form-level duplicate validation to keep in sync.

## 2. Architecture Practices

### ✅ Good — `summary.py` is a pure module with zero HTTP awareness
`per_tester()` and `per_project()` take no `request`, return plain dicts, and are unit-tested
directly without a test client. The one grouping helper, `_months()`, is shared by both
public functions via a `label` parameter rather than duplicated per caller.

### ✅ Good — Thin views via four shared dispatch helpers
`_add`, `_edit`, `_delete`, `_filter` carry the app's entire non-trivial view logic; every
public view (`time_add`, `pay_edit`, `tester_delete`-shaped functions, etc.) is a one- or
two-line wrapper. A fourth CRUD model would cost roughly four one-liners, not four new view
classes.

### ⚠️ Bad — The `project`-filter guard on `Payment` is implicit duck-typing
`_filter()`'s `qs.filter(project=proj) if hasattr(qs.model, "project") else qs` (`views.py`)
silently no-ops the `project` querystring parameter for `Payment` (which has no `project`
field), relying on `hasattr` rather than a documented per-model filter contract. It works and
is tested indirectly, but a reader has to infer the intent from the one-liner rather than see
it stated.
🔧 **How to improve:** a one-line comment at the `hasattr` check, or split `_filter` into two
thin model-specific wrappers if the shared version's implicitness becomes confusing.

### ⚠️ Bad — No confirmation step before delete
`time_delete`/`pay_delete` (`_delete` in `views.py`) delete on any POST with no "are you
sure" interstitial and no soft-delete. Low-stakes for a single-operator local tool, but an
accidental click on the inline "del" button in `time_list.html`/`pay_list.html` is
unrecoverable.
🔧 **How to improve:** a confirm page, or at minimum a client-side `confirm()` on the delete
button, before this app ever gets a second user.

## 3. Security & Robustness Practices

### ✅ Good — CSRF protection is on everywhere, despite no-auth
Every mutating form — add, edit, and the inline one-button delete forms — carries
`{% csrf_token %}`. Not skipped just because authentication was skipped.

### ✅ Good — CSV formula-injection guard, correctly scoped and separately committed
`export._csv_safe()` prefixes a leading `=`, `+`, `-`, `@`, tab, or CR with a single quote —
the OWASP-documented trigger set — applied uniformly to every exported field. It shipped as
its own commit (`2d7f002`) after the export feature itself (`319c96a`), with a dedicated
regression test asserting both the prefix and the absence of the raw unguarded string.

### ✅ Good — Iterative, test-pinned filter hardening against three real 500 vectors
Three consecutive `fix(timesheet):` commits in one session closed a malformed-month string, a
tester id too large for SQLite's integer range, and a Unicode digit (`"²"`, `"①"`) that
passes `str.isdigit()` but fails `int()` — each with its own regression test and an inline
comment naming the exact failure ("was 500: date year 0 out of range").

### ⚠️ Bad — No-auth posture is a hub-level assumption, unstated at the app level
Nothing in `timesheet/` — no comment, no docstring — records that the entire app's safety
depends on the hub staying bound to `127.0.0.1`. The design doc's "Out of scope (v2+)" list
mentions authentication only as a deferred feature, not as a stated current-risk boundary.
🔧 **How to improve:** a short comment near the top of `views.py` or next to
`ALLOWED_HOSTS` in `hub/settings.py` naming the assumption and what would need to change
(auth, per-row ownership) before this app could be exposed beyond loopback.

### ⚠️ Bad — `DEBUG = True` in the settings module timesheet is served from
Verified on `origin/main`'s `hub/settings.py`. Bounded today by `ALLOWED_HOSTS`, but any
unhandled exception in a `timesheet` view renders a full traceback rather than a generic
error page. Hub-wide, not timesheet-specific, but worth flagging since it's part of this
app's serving path.
🔧 **How to improve:** flip to `DEBUG = False` with a custom 500 template, or at minimum note
in the hub's own docs why `DEBUG = True` is considered acceptable for a loopback-only service.

## 4. Code Quality Practices

### ✅ Good — Zero new third-party dependencies
The entire feature — models, aggregation, views, forms, CSV export, templates — uses only
Django and the stdlib already in the hub's `requirements.txt`.

### ✅ Good — `on_delete=PROTECT` on both FKs to `Tester`
Deleting a tester with existing time entries or payments raises `ProtectedError` rather than
cascading or silently orphaning rows — the correct default for financial records.

### ⚠️ Bad — No lint or type gate
No ruff, no mypy, no config for either; `manage.py test` is the only automated check found in
the app or its CI wiring. The code reads clean today, but nothing enforces it going forward.
🔧 **How to improve:** add `ruff check` to the hub's CI across the whole repo, not just
`timesheet/` — cheap insurance, especially now that the hub has its first real CRUD surface.

## 5. Testing Practices

### ✅ Good — Assertions are hand-derived, not smoke checks
`Decimal("35.00")` from `3.50h × $10.00`; a two-entry/one-payment fixture asserted against a
hand-computed `balance`; drill-down rows asserted by exact date, project, hours, and amount.

### ✅ Good — Regression tests carry the incident in their name and comment
`test_list_graceful_on_year_zero_month` and `test_list_graceful_on_huge_tester_id` include
inline comments naming the exact prior failure ("was 500: date year 0 out of range" / "was
500: int too large for SQLite") — a reader doesn't have to dig through git blame to know why
the test exists.

### ✅ Good — Security fix tested against its exact payload class
`test_csv_injection_neutralized` uses `project="=cmd()"` and `description="=SUM(A1:A2)"` —
the literal attack shape the guard defends against — and asserts both that the quote-prefix
is present and that the raw unguarded string is absent.

### ⚠️ Bad — No fixture exercises the rounding-disagreement case (§1)
Every `test_summary.py` fixture uses hours/rate pairs whose products land on exact cents
(`2×10`, `3×20`), so the summary's sum-then-round `earned` and `TimeEntry.amount_usd`'s
round-per-entry method always agree in the suite — the one place they could visibly diverge
is untested.
🔧 **How to improve:** add a fixture with an hours/rate pair whose product needs rounding
(e.g. three entries where the unrounded sum rounds differently than the sum of individually-
rounded entries) and assert the current, documented behavior.

### ⚠️ Bad — `on_delete=PROTECT` has no regression test
The one referential-integrity guarantee in the model layer — deleting a `Tester` with
existing entries/payments should raise `ProtectedError` — has no `assertRaises` test anywhere
in the suite.
🔧 **How to improve:** one test per FK (`TimeEntry`, `Payment`) asserting the delete is
blocked.

## 6. Documentation Practices

### ✅ Good — Design doc and implementation plan match the shipped code exactly
`docs/superpowers/specs/2026-09-01-testers-timesheet-design.md` and
`docs/superpowers/plans/2026-09-01-timesheet.md` describe precisely the models, aggregation
logic, URLs, and CSV columns that exist on `origin/main` — committed the same session as the
code, so there is no drift to reconcile.

### ✅ Good — In-code rationale for the money model
The design doc states "Money + hours are `DecimalField` (never float — accounting-safe)" and
"`amount_usd` = property … derived, never stored — no drift" as explicit decisions, not
inferred after the fact. `_months()`'s own docstring explains its rounding choice relative to
the top-level summary figure.

### ⚠️ Bad — The reconciliation caveat (§1) is documented nowhere a bookkeeper would see it
Not in the summary template, not in the CSV export, not in a README — only discoverable by
reading `summary.py` and `models.py` side by side.
🔧 **How to improve:** see §1's fix — one sentence, visible from the summary page or the CSV
header comment, stating the two conventions can differ by a cent.

### ⚠️ Bad — No app-level README
Reasonable for an app this size inside a larger repo, but a newcomer to `wegofwd-hub` has to
find the superpowers spec/plan docs (or this critique) to learn what `timesheet/` does — there
is no `timesheet/README.md` or module docstring at the top of `views.py`/`models.py` serving
that purpose.

---

*First review (v1.0). Findings verified against `wegofwd-hub`'s `origin/main` at `dd7d888`
via `git show`; test counts and behavior read from source, not run locally (no Django install
in the review environment). Cost analysis maintained privately.*
