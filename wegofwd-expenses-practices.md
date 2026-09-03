# wegofwd-expenses — Good Practices, Bad Practices & How to Improve

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

**Document type:** Engineering practices analysis
**Scope:** Python 3.11+ email→ledger expense pipeline — six packages
(`mailfetch`, `billclassify`, `billextract`, `ledger`, `expensereport`,
`expenseweb`), reviewed against `origin/master` at `aaa7fb3`.
**Period:** 2026-09-03 (v1.0 — first review)
**Related:** [wegofwd-expenses-critique.md](wegofwd-expenses-critique.md) · [wegofwd-expenses-development-pattern.md](wegofwd-expenses-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve

---

## Table of Contents

1. Architecture Practices
2. Financial-Correctness Practices
3. Security & Credential-Handling Practices
4. Code Quality Practices
5. Testing Practices
6. Operational / Deployability Practices

---

## 1. Architecture Practices

### ✅ Good — Stages coupled only through on-disk artifacts
No package imports another's internals; `mailfetch` → `billclassify` →
`billextract` → `ledger` → `expensereport` hand off through JSONL → SQLite →
Markdown (`run_pipeline.sh`). Any stage can be rerun, inspected, or replaced
without touching the others' code.

### ✅ Good — The LLM never chooses control flow
`ADR-0001`'s constraint is enforced structurally: the LLM appears only inside
`classify_llm` and `extract_row`, both of which produce a value that
deterministic code then validates. No LLM output decides which stage runs
next or whether a record posts.

### ✅ Good — A cheap deterministic tier gates the expensive LLM tier
`classify_heuristic` (`packages/billclassify/billclassify/heuristics.py`)
resolves known billers and subject-keyword matches without an LLM call;
`classify_llm` only runs for what the heuristic tier can't resolve.

### ⚠️ Bad — No CI wires any of this together
Six packages, each with its own `pyproject.toml` and test suite, and nothing
in the repo runs `pytest` automatically. A regression is caught only if a
human runs the suite.
🔧 **How to improve:** one `.github/workflows/ci.yml` matrix-running `pytest`
across all six `packages/*/` directories (plus `tests/`) would close this at
low cost — the suite is fast (130 tests in a few seconds total).

## 2. Financial-Correctness Practices

### ✅ Good — Money is `Decimal`-as-`TEXT`, never `float`, throughout
`ledger/schema.py` stores amounts as SQLite `TEXT`; every arithmetic path
(`pricing.cost_usd`, `apply_amount_category`, report aggregation) routes
through `decimal.Decimal`. `ADR-0003` states this is test-enforced, and this
review's read of the code confirms no `float` touches an amount.

### ✅ Good — Idempotency key is a real identity, not a derived one
`ledger/store.py`'s `message_id UNIQUE` constraint means a rerun of the
pipeline against the same mail can never double-post an entry — the key is
Gmail's own message id, not something computed from content that could
collide or drift.

### ✅ Good — Duplicate-suspect detection is scoped correctly for refunds
The secondary `(vendor, invoice_number)` duplicate check is additionally
scoped by `entry_type`, so a refund reusing its original charge's invoice
number is not flagged as a duplicate charge (`test_refund.py`,
`test_dedup_and_rollback.py` cover this). A naive scope here would have
produced false-positive duplicate flags on every refund.

### ✅ Good — A duplicate suspect is flagged, never silently merged
`ADR-0003`: "surfaced in the report — never silently merged." `UpsertResult`
carries `duplicate_suspects` as a list the report can render, rather than the
store making a merge decision on the caller's behalf.

### ⚠️ Bad — Cost data is not backfilled for pre-`aaa7fb3` ledger rows
Entries posted before the cost-capture feature landed have no `cost_usd` /
`llm_usage` data — additive by design (§ development-pattern Decision 6), but
worth flagging before treating the cost column as a complete cost-of-running
history.
🔧 **How to improve:** note the cutover commit in the report's output (or a
footnote) when the cost column is used for a month that straddles it.

## 3. Security & Credential-Handling Practices

*(Findings below are general classes — no exploit recipe, no real credential
value.)*

### ✅ Good — Uniform credential precedence, enforced not just documented
`billextract/_credentials.py`'s `get_api_key` and `gmail_client.py`'s
`_load_credentials` both resolve: env var → `~/.config/wegofwd/` file → an
interactive fallback (prompt for the API key; OAuth consent flow for Gmail).
Neither silently falls back to a hardcoded or empty value.

### ✅ Good — A loose file permission on a secret file is a hard error, not a warning
`get_api_key` checks the API-key file's mode before reading it and raises
`CredentialError` naming the exact fix (`chmod 600`) if it's looser than
`0600` — it does not read a world-readable key file "just this once."

### ✅ Good — Credential values are never logged
Every error path in `gmail_client.py` and `_credentials.py` names a *path* to
check (`TOKEN_PATH`, `CLIENT_SECRET_PATH`) or a *provider* name in its
message, never the secret's content.

### ✅ Good — `.gitignore` covers the right classes and it's actually clean
`token.json`, `*.credentials`, `.env`, and the whole `data/` tree (raw email
bodies/attachments) are excluded; this review confirmed none of them appear
in `origin/master`'s tree.

### ⚠️ Bad — Redaction before the LLM call covers two pattern classes only
`redact.py` strips SSN and card-number-shaped digit runs; it does not touch
names, addresses, phone numbers, or tracking-link tokens that appear in a
real vendor email body. Honestly labeled "recall-biased" in the docstring, but
not documented anywhere as an explicit accepted trade-off the way the ADRs
document other security-relevant decisions.
🔧 **How to improve:** add a fourth ADR (or a comment in `redact.py` pointing
to one) stating plainly that general PII in email bodies is sent to the LLM
provider, and why — so the scope is a documented decision, not an implicit
one a reader has to discover by opening the file.

## 4. Code Quality Practices

### ✅ Good — Typed exception hierarchies with actionable messages
`MailAuthError`, `MailHistoryExpiredError`, `MailMessageGoneError`
(mailfetch), `LedgerWriteError` (ledger), `ExtractionError` (billextract),
`CredentialError` (both credential modules) — each error message names what
to check or do next, not just what failed.

### ✅ Good — An unknown LLM model is priced conservatively, not at zero
`billextract/pricing.py`'s `DEFAULT_RATE` falls back to the known
(`claude-sonnet-4-6`) rate for an unrecognized model, with the reasoning
stated in a comment: a silent `$0` would hide real spend in a financial
ledger, which is worse than a small mis-estimate.

### ✅ Good — Negative-input clamping is explicit, not incidental
`cost_usd` clamps negative token counts to zero before pricing rather than
letting a negative value flow into the arithmetic and produce a negative
cost — a small defensive detail in a function that feeds a financial column.

### ⚠️ Bad — No lint or type gate anywhere
No `ruff`, no `mypy`, no config for either across all six `pyproject.toml`
files. The code reads consistently typed and styled, but nothing enforces it.
🔧 **How to improve:** add `ruff check` to the CI workflow recommended in §1;
cheap given the codebase's existing consistency.

## 5. Testing Practices

### ✅ Good — 130 tests, verified passing by this review (not merely cited)
This review ran `pytest -q` in each of the six packages directly: billclassify
19, billextract 39, expensereport 16, expenseweb 8, ledger 13, mailfetch 34,
plus 1 at the top level — all green. This is a real, current count, not a
repetition of the "76/76" figure from the 2026-07-06 merge commit message
(which was accurate then; 54 tests have been added since).

### ✅ Good — The suite names its own gaps in the source, not just in a coverage tool's output
`gmail_client.py`'s docstring states plainly that it is "Deliberately NOT
unit-tested" and why; `test_fixtures.py::test_invoice_with_pdf_attachment_
body_sufficient_never_touches_pdfminer`'s own docstring explains that
pdfminer's real extraction path is untested here and where it *is* exercised.
A reader does not need a coverage report to know where the suite's edges are.

### ✅ Good — The Gmail error-mapping boundary is tested one layer below the fake
`test_gmail_errors.py` builds real `googleapiclient.errors.HttpError` objects
and drives them through `GmailClient`'s actual status-mapping methods
(`_http_status`, `get_message`, `_list_ids_since_history`) — this is a
genuine unit test of the boundary code, distinct from and complementary to
`FakeGmail`'s higher-level fake in `test_fetch.py`.

### ✅ Good — Every named production bug fix has a paired regression test
First-run lookback bounding (`test_lookback.py`), the historyId-vs-message-id
bug (`test_high_water_mark_is_client_history_id_not_message_id`), doc_date
sanity (`test_doc_date_sanity.py`), refund handling (`test_refund.py`) — each
corresponds to a named `fix:` commit in the git log, and this review confirmed
each test still exists and passes at `aaa7fb3`.

### ⚠️ Bad — No coverage percentage is measurable
`pytest-cov` is not configured anywhere; the review can report pass/fail
counts but not what fraction of lines is exercised.
🔧 **How to improve:** add `pytest-cov` to each package's dev dependencies and
wire a coverage line into the CI workflow from §1.

### ⚠️ Bad — No fuzz/property tests on the redaction regexes
`redact.py`'s `_CARD` and `_SSN` patterns are exercised only against
hand-picked strings.
🔧 **How to improve:** a small property test (formatting variants — dashes,
spaces, spacing around groups) would at least confirm the two classes
`redact.py` claims to catch are caught reliably.

## 6. Operational / Deployability Practices

### ✅ Good — State advances only on success
`fetch_new` raises before producing a new state on an auth failure;
`run_pipeline.sh`'s `run_stage` halts on any stage's non-zero exit before the
cursor file is touched. A partially-failed run cannot silently skip mail.

### ✅ Good — The documented cursor-expiry recovery path has fired in production and worked
This review found direct evidence (`last_run_state.json.stale-histid-326897`,
dated 2026-07-12) that a Gmail history cursor did age past the platform's
retention window in production, and the pipeline's designed resync (a bounded
lookback query, same as a first run) recovered it without manual
intervention — the documented gotcha and the documented fix both happened for
real, not just in a test.

### ✅ Good — A cron-safe lockfile that tolerates crash-leftover locks
`run_pipeline.sh` exits 0 (not an error) if a live PID holds the lock, and
ignores a lock left by a dead PID — correct behavior for unattended daily
cron use where a stale lock must never permanently wedge the pipeline.

### ✅ Good — A non-fatal secondary step doesn't mask the primary result
`cron_run.sh` regenerates the HTML dashboard after the pipeline runs and
explicitly continues past a render failure — so a dashboard hiccup can't hide
whether the actual ingest succeeded, which is the status that matters for
noticing a broken run.

### ⚠️ Bad — No retention/rotation for `runs/` directories or cron logs
Two months of daily cron use has produced ~60 run directories and per-day
cron logs on disk with no pruning step in either script. Not urgent yet, but
unbounded.
🔧 **How to improve:** a `--retain-days`-style prune step in `cron_run.sh`,
mirroring the `data/` retention already planned for raw bodies/attachments.

### ⚠️ Bad — No alerting on a halted pipeline
A stage failure is logged to the day's cron log and the script exits
non-zero, but nothing notifies a human. A halted ingest is discoverable only
by reading a log or noticing the ledger hasn't grown.
🔧 **How to improve:** even a minimal local notification or self-addressed
email on non-zero exit from `cron_run.sh` would close this cheaply for a
single-user tool.

---

*First review (v1.0). Findings verified against `origin/master` at `aaa7fb3`,
a local `pytest` run in each of the six packages (130 passed, 0 failed), and
the live runtime state (crontab, run directories, cron logs, ledger cursor)
on the machine that runs the daily cron. No real financial data, vendor
names, or amounts from that runtime state are reproduced here. Cost analysis
maintained privately.*
