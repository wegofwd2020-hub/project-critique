# wegofwd-expenses — Code Review & Critique

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

**Reviewed:** 2026-09-03 (v1.0 — first review, against `master` at `aaa7fb3`)
**Anchor:** `aaa7fb3` (2026-08-01)

**Repo:** `wegofwd-expenses` (private, GitHub org), default branch `master`
**Phase:** Pre-1.0, no release tags (commit-based). Six independently-installable
packages, no CI, no lint/type gate.
**Scope:** Deterministic email→ledger expense pipeline for a single WeGoFwd
mailbox. Five fixed stages — `mailfetch` (Gmail API) → `billclassify`
(heuristic + LLM fallback) → `billextract` (LLM structured extraction +
pdfminer.six for PDF attachments) → `ledger` (idempotent SQLite writer) →
`expensereport` (Markdown report) — plus `expenseweb` (self-contained HTML
dashboard). The LLM is confined to classification and extraction; it never
chooses control flow (ADR-0001).
**Rating key:** ✅ Strong · ⚠️ Gap / Risk · ❌ Critical Issue
**Related:** [wegofwd-expenses-development-pattern.md](wegofwd-expenses-development-pattern.md)
· [wegofwd-expenses-practices.md](wegofwd-expenses-practices.md)

> **Note on scope.** This is an internal single-user ops tool with no external
> attack surface (no inbound network listener; it reads one mailbox and calls
> one LLM provider on a local cron). It is a finance tool — it handles a Gmail
> OAuth token and an Anthropic API key, and reads real financial PDFs at
> runtime. No real expense data lives in the repo (it's gitignored and stays
> on disk under `~/.local/share/wegofwd-expenses/`), so this review is of the
> **code**, not of any customer or personal financial data. Credential and
> secret-handling findings below are stated as general classes (what the code
> does with a class of secret), not as a recipe against a specific value.

---

## Executive Summary

The most important finding in this review is a **correction to prior
tracking, not a code defect**: the pipeline is not in an untested,
dry-run-pending state. It has been running as a **live daily cron against the
real mailbox since 2026-07-06**, continuously through this review's measurement
date (60 recorded run directories, a real SQLite ledger with entries spanning
March–August 2026 doc dates, and a Gmail `historyId` cursor that has advanced
from a first run to `395672` as of 2026-09-02). The commit-log framing of "76/76
tests, real-mailbox dry run pending" describes the state at the 2026-07-06
merge; `aaa7fb3` (2026-08-01) is materially past that, and the runtime evidence
on the machine that runs the cron shows real Gmail, real LLM, and real
pdfminer calls happening daily, not a rehearsal. This review found direct
evidence that the one production risk this project's own docs and past notes
called out — a Gmail history cursor older than the ~1-week retention window —
**actually occurred in production on 2026-07-12** and self-healed via the
documented lookback-resync path, exactly as designed.

The code underneath that live system is disciplined. ADR-0001's "pipeline, not
agent" framing is enforced structurally, not just stated: five packages
communicate only through on-disk JSONL/SQLite/Markdown artifacts, and the LLM
touches exactly two stages, both confined to producing a value the caller then
validates against a schema — it is never given the chance to decide what
happens next. Money is `Decimal`-as-`TEXT` everywhere (test-enforced), the
ledger's idempotency key (`message_id` UNIQUE) makes re-running a stage safe,
and a second `(vendor, invoice_number, entry_type)` check flags duplicate
*suspects* rather than silently merging them — with the non-obvious refinement
that a refund is allowed to reuse its original charge's invoice number without
being flagged. The project also tracks the cost of running itself: every
extraction attaches its own token usage and a computed USD cost to the ledger
row it produced, with an unknown model priced at the known model's rate rather
than a misleading zero.

What is genuinely thin: there is **no CI and no lint/type gate anywhere in the
repo** — six packages, 130 tests, and nothing runs any of them except a human
or a cron invocation of the pipeline itself. `redact.py`, the one thing
standing between an email body and the Anthropic API, catches exactly two
pattern classes (SSN, card number) and is honestly labeled "recall-biased" —
but that means ordinary PII in a vendor email (names, addresses, tracking
links) reaches the LLM verbatim, which is a reasonable and probably necessary
trade-off for extraction quality, but is not documented as a decision anywhere
the way the ADRs document the other trade-offs. And the one true blind spot in
the test suite — `gmail_client.py`'s real OAuth/HTTP wiring and the actual
`pdfminer` extraction call — is *explicitly* named as untested in both the
module docstring and a test's own comment, which is the right way to leave a
gap, but the artifact those docstrings point to ("the manual dry run") is
stale: that path is no longer a manual rehearsal, it is what runs at 07:00
every day.

**Verdict:** A well-scoped, honestly-documented internal tool whose test suite
tells the truth about what it does and doesn't cover, running for real in
production for two months with no reported failure that didn't self-heal. The
gaps are process (no CI/lint gate) and one narrow, undocumented trade-off
(redaction scope) — not architectural.

## Snapshot

| Dimension | Measured at `aaa7fb3` |
|---|---|
| Packages | 6 (`mailfetch`, `billclassify`, `billextract`, `ledger`, `expensereport`, `expenseweb`) |
| Tests | **130 passing**, verified by a local `pytest` run per package this review |
| Test files | 26 across the 6 packages + 1 top-level `tests/test_pipeline.py` |
| CI | **None** — no `.github/workflows`, no other CI config found |
| Lint/type gate | **None** — no ruff/mypy config anywhere in the tree |
| Coverage tool | Not configured (no `pytest-cov`); no % measured |
| ADRs | 3 (`0001` pipeline-not-agent, `0002` mail/PDF choice, `0003` money/dedup) |
| Production status | **LIVE** — daily cron since 2026-07-06, 60 run directories through 2026-09-02, real Gmail historyId cursor progressing |
| Dependencies (core) | `wegofwd-llm`, `pdfminer.six`, `google-api-python-client` family (mailfetch only) |
| Secrets in repo | None found; `.gitignore` excludes `token.json`, `*.credentials`, `.env`, `data/` |
| TODO/FIXME | none found in a grep of the packages |

## 1. Architecture

### Strengths
- ✅ **The pipeline-not-agent boundary is structural.** Stages are separate
  pip-installable packages (`packages/<name>/pyproject.toml`, its own
  `[project.scripts]` entry point) that never import one another's internals —
  they hand off through on-disk JSONL → SQLite → Markdown artifacts
  (`ADR-0001`). The LLM appears in exactly two stages (`billclassify`,
  `billextract`), and in both it produces a value that a schema/confidence
  gate then judges — it never decides what stage runs next or whether a
  record is trustworthy. `run_pipeline.sh` is the only thing that sequences
  stages, and it is a plain bash script with an explicit halt-on-failure rule.
- ✅ **Two-tier classification keeps the LLM off the cheap path.**
  `classify_heuristic` (`packages/billclassify/billclassify/heuristics.py`)
  resolves known billers and subject-keyword matches deterministically and
  only escalates to `classify_llm` for genuinely ambiguous mail — the LLM is
  a fallback tier, not the default path, which matters for both cost and
  determinism.
- ✅ **State only advances on success.** `fetch_new` raises before producing a
  new high-water mark on an auth failure (`packages/mailfetch/mailfetch/fetch.py`),
  and `run_pipeline.sh`'s `run_stage` helper exits non-zero without touching
  `last_run_state.json` if any stage fails — a partially-failed run cannot
  silently advance the cursor past unprocessed mail.
- ✅ **Cost-of-self is a first-class artifact, not an afterthought.**
  `billextract.pricing.cost_usd` converts each extraction's actual token usage
  into a USD figure that rides along on the ledger row it produced
  (`extract_row` in `packages/billextract/billextract/extract.py`), and an
  unrecognized model is priced at the known model's rate rather than $0 — a
  deliberate choice documented in the module docstring so real spend is never
  silently hidden by a "zero-cost" placeholder.

### Gaps & Risks
- ⚠️ **No CI.** There is no `.github/workflows` directory and no other CI
  config in the tree. The 130 tests this review found and ran are real and
  pass, but nothing runs them automatically on a push or PR — a regression is
  only caught if a human remembers to run `pytest` in each of six packages.
- ⚠️ **`redact.py`'s scope is undocumented as a decision.** ADR-0002 and
  ADR-0003 record real architectural trade-offs; there is no ADR or comment
  explaining that redaction is deliberately narrow (see §5) versus an
  oversight. Given this is the one function standing between an email body
  and a third-party LLM call, it deserves the same explicit trade-off
  treatment the other security-relevant decisions got.

## 2. Code Quality

### Strengths
- ✅ **Consistent credential precedence across two packages.**
  `billextract/_credentials.py` and `billclassify` both resolve a provider key
  via env var → `~/.config/wegofwd/<name>` file → interactive prompt, and the
  file path enforces mode `0600` before reading it — an insecure permission
  raises a typed `CredentialError` naming the fix (`chmod 600`) rather than
  reading the key anyway. The precedence and the "never logged, never
  hardcoded" rule are stated once in the docstring and actually followed in
  the one place that reads keys.
- ✅ **Typed exception hierarchies per package**, each with an actionable
  message: `MailAuthError`, `MailHistoryExpiredError`, `MailMessageGoneError`
  (mailfetch), `LedgerWriteError` (ledger), `ExtractionError` (billextract).
  `gmail_client.py`'s error mapping is itself unit-tested against real
  `googleapiclient.errors.HttpError` objects (see §3), not just faked at the
  top of the call stack.
- ✅ **Decimal discipline is enforced, not just claimed.** `ledger/schema.py`
  stores every amount as SQLite `TEXT`; `pricing.cost_usd` and
  `apply_amount_category` route every amount through `decimal.Decimal`; no
  `float` touches money anywhere this review found, matching ADR-0003.
- ✅ **The refund/duplicate distinction in `ledger/store.py` is a genuine
  correctness catch.** A duplicate-suspect match is scoped to
  `(vendor, invoice_number, entry_type)`, not just `(vendor, invoice_number)`
  — a refund legitimately reuses its original charge's invoice number, and
  without the `entry_type` scope every refund would falsely flag as a
  duplicate charge. The commit history (`fix: model refunds/credits so they
  net against charges`) shows this was found and fixed, and the test suite
  covers it (`test_refund.py`, `test_dedup_and_rollback.py`).

### Gaps & Risks
- ⚠️ **`redact.py` catches exactly two pattern classes.** `_CARD` (13–16
  contiguous digits) and `_SSN` (`\d{3}-\d{2}-\d{4}`) are the entire redaction
  surface before an email body is sent to the LLM. Names, addresses, phone
  numbers, and tracking-link tokens embedded in a real vendor email pass
  through unredacted — reasonable for extraction quality (the LLM needs
  context to find the vendor/amount/date), but it means the practical
  redaction guarantee is narrower than "PII redacted before LLM" might imply
  to a reader who hasn't opened the file. This review did not find any place
  the pipeline claims broader redaction than it delivers, but neither does it
  say the guarantee is this narrow.
- ⚠️ **No lint or type gate anywhere.** No `ruff`, no `mypy`, no config for
  either in any of the six `pyproject.toml` files. The code reads
  type-annotated and consistent in style, but nothing enforces it.

## 3. Test Coverage

### Strengths
- ✅ **130 tests, verified passing by this review** (a local `pytest -q` run
  in each of the six packages plus the top-level `tests/`), broken down:
  billclassify 19, billextract 39, expensereport 16, expenseweb 8, ledger 13,
  mailfetch 34, top-level pipeline 1. This is up from the 76 reported at the
  2026-07-06 merge — the suite has grown by 54 tests across the 21 commits
  since, and every one of those commits' `fix:` messages (first-run lookback,
  doc-date sanity, model refunds, stale-cursor resync) has a matching
  regression test this review confirmed exists and passes.
- ✅ **The suite documents its own gaps, in the source, honestly.**
  `gmail_client.py`'s module docstring states outright: "Deliberately NOT
  unit-tested: mocking the full Google API client is out of scope... exercised
  only... in a live mailbox." `test_fixtures.py::test_invoice_with_pdf_
  attachment_body_sufficient_never_touches_pdfminer` names in its own
  docstring that pdfminer is untested here and the real PDF path is exercised
  elsewhere. This is the right way to leave a gap — the artifact says so where
  a reader will find it, rather than a coverage report silently having a hole.
  (§ Executive Summary notes that the artifact those two docstrings point to —
  "the manual dry run" / "a live mailbox" — describes a rehearsal that has
  since become the actual daily production path; the docstrings should be
  refreshed to say so, but the underlying honesty pattern is sound.)
- ✅ **The Gmail error-mapping boundary is tested against real exception
  types, not just a fake.** `test_gmail_errors.py` constructs real
  `googleapiclient.errors.HttpError` objects with a stand-in `Response` and
  drives them through `GmailClient`'s actual status-mapping code
  (`_http_status`, `get_message`, `_list_ids_since_history`) — a 404 on
  `messages.get` becomes `MailMessageGoneError`, a 404 on `history.list`
  becomes `MailHistoryExpiredError`, anything else becomes `MailAuthError`.
  This is a real boundary test one layer below `FakeGmail`, not a duplicate of
  it.
- ✅ **`test_lookback.py` and `test_fetch.py` cover the two idempotency bugs
  this project's own history says it shipped and then fixed**: a first run
  that ignored `lookback_days` and would have pulled the entire mailbox, and a
  high-water mark that was almost the last message id instead of the client's
  own `historyId` (`test_high_water_mark_is_client_history_id_not_message_id`
  names the exact regression it guards against in its docstring).

### Gaps & Risks
- ⚠️ **No coverage percentage is measurable.** `pytest-cov` is not a
  dependency anywhere; this review can report test counts and that they pass,
  not what fraction of lines they exercise.
- ⚠️ **The redaction regexes have no fuzz/property coverage** — only
  hand-picked strings are tested. Given `redact.py`'s narrow, honestly-labeled
  scope (§2), a property test would at least confirm the two patterns it does
  claim to catch are caught reliably across formatting variants (dashes,
  spaces, Unicode digit look-alikes).

## 4. Documentation

### Strengths
- ✅ **Three tight ADRs record real trade-offs**, not just decisions:
  `0001` names the cost of the pipeline-not-agent choice (artifact I/O, field
  duplication across JSONL lines), `0002` names the cost of Gmail-over-IMAP
  (heavier deps, OAuth flow) and pdfminer-over-poppler (no system binary), and
  `0003` names the cost of Decimal-as-TEXT (reconstructing Decimal from TEXT
  in the report) and the never-silently-merge dedup rule.
- ✅ **Docstrings carry the same discipline as the ADRs** — the two
  deliberately-untested boundaries are named in the code itself (§3), and
  `run_pipeline.sh`'s and `cron_run.sh`'s comments explain the lockfile,
  environment assumptions, and the non-fatal dashboard-render step in enough
  detail to operate the system from the script alone.

### Gaps & Risks
- ⚠️ **The README does not reflect that the pipeline is live in production.**
  It documents how to run the pipeline manually but says nothing about the
  daily cron, the data directory layout, or that real financial data has been
  accumulating in `~/.local/share/wegofwd-expenses/ledger.sqlite` since
  2026-07-06. A reader of the repo alone would reasonably conclude this is
  still pre-dry-run, which — per the Executive Summary — is no longer true.
- ⚠️ **No CHANGELOG.** The commit log is legible (`fix(mailfetch): ...`,
  `feat(expenses): ...`) but there is no single place that narrates the
  post-merge hardening arc (lookback bound → doc-date sanity → refund
  handling → stale-cursor resync → cost capture) the way this critique had to
  reconstruct it from `git log`.

## 5. Security & Safety

*(Findings are stated as general classes per this review's scope — no exploit
recipe, no real credential or financial value.)*

### Strengths
- ✅ **Credential precedence is uniform and enforced, not just documented.**
  Both the Gmail token and the Anthropic API key follow env var → file (mode
  checked) → prompt, and the file path is never read if its permissions are
  looser than `0600` — the code raises rather than silently trusting a
  world-readable secret file.
- ✅ **The OAuth token is cached at `0600` and never logged.**
  `GmailClient._cache_token` sets the mode explicitly after writing; error
  messages throughout `gmail_client.py` name the *path* to check, never the
  credential *content*.
- ✅ **`.gitignore` covers the right classes of sensitive artifact** —
  `token.json`, `*.credentials`, `.env`, and the entire `data/` tree (raw
  email bodies and attachments) are excluded, and this review confirmed none
  of them are tracked in `origin/master`.
- ✅ **Idempotency protects financial integrity, not just convenience.** The
  `message_id` UNIQUE constraint means re-running a stage after a partial
  failure cannot double-insert a ledger entry — a property that matters more
  for a financial ledger than for most idempotent-retry designs.

### Gaps & Risks
- ⚠️ **Redaction is a narrow class filter, not general PII scrubbing** (see
  §2) — worth an explicit ADR given the data class involved (financial email
  content sent to a third-party API).
- ⚠️ **`gmail_client.py`'s real wire behavior is validated only by production
  use, not by an automated test.** This is a documented, deliberate choice
  (§3) rather than an oversight, but it means a regression in the actual
  Google API interaction (as opposed to `mailfetch`'s own logic around it)
  would surface first as a production failure, not a test failure.

## 6. Scalability & Operations

### Strengths
- ✅ **Idempotency and cursor recovery are proven in production, not just in
  tests.** This review found a backup state file
  (`last_run_state.json.stale-histid-326897`, dated 2026-07-12) that is direct
  evidence the Gmail history-retention gotcha this project's own design
  anticipated actually happened once in production, and the pipeline recovered
  via the documented bounded-lookback resync (`fetch.py`'s
  `MailHistoryExpiredError` handling) rather than requiring manual
  intervention. The cursor has continued advancing normally since.
- ✅ **The lockfile is a real single-writer guarantee for cron use.**
  `run_pipeline.sh` checks a PID-bearing lockfile and exits 0 (not an error)
  if a live run holds it, and ignores a stale lock from a dead PID — the
  right behavior for a daily cron that must never overlap itself but also
  must never wedge on a crashed run's leftover lockfile.
- ✅ **The dashboard render is explicitly non-fatal.** `cron_run.sh` runs
  `expenseweb` after the pipeline and continues past its failure — a render
  hiccup can't mask the pipeline's own exit status, which is the status that
  actually matters for alerting on a broken ingest.

### Gaps & Risks
- ⚠️ **No log rotation/retention policy for cron logs or `runs/` directories**
  found in the scripts — this review found ~60 run directories and per-day
  cron logs accumulating since 2026-07-06 with no pruning step in
  `cron_run.sh` or `run_pipeline.sh`. Not urgent at two months of daily
  volume, but worth a `--retain-days`-style bound before it is.
- ⚠️ **No alerting on a halted pipeline.** `run_pipeline.sh` exits non-zero
  and logs to the day's cron log on a stage failure, but nothing this review
  found notifies a human — a failed run is discoverable only by reading the
  log or noticing a stale ledger.

## Priority Actions

1. ⚠️ **Refresh the docstrings and README to reflect production reality.**
   `gmail_client.py`'s "exercised only... in a live mailbox" and
   `test_fixtures.py`'s "manual dry run" language both predate what is now a
   two-month-old daily production cron — the honesty pattern is good, the
   referent is stale.
2. ⚠️ **Add CI** — even a single workflow running `pytest` across all six
   packages on push would close the largest process gap this review found,
   given the suite is real and fast (130 tests run in seconds).
3. ⚠️ **Document the redaction scope as a decision** (a fourth ADR, or a
   comment in `redact.py` pointing to one) — state explicitly that general PII
   in email bodies is sent to the LLM, and why that trade-off was accepted.
4. ⚠️ **Add a lint/type gate** (ruff at minimum) — cheap insurance now, before
   a seventh package or a larger contributor pool makes style drift costly to
   unwind.
5. ⚠️ **Add a basic failure alert** for the daily cron (even a local desktop
   notification or a one-line email-to-self on non-zero exit) so a halted
   ingest is noticed the same day rather than discovered later.

---

*Reviewed against `master` at `aaa7fb3` (2026-08-01), the current tip of
`origin/master` at review time. All test counts were verified by running
`pytest` locally in each of the six packages (130 passed, 0 failed). Production
status was verified by reading the live cron installation (`crontab -l`) and
the runtime data directory (`~/.local/share/wegofwd-expenses/`) on the machine
that runs it — run directories, cron logs, and the ledger's cursor state —
not from documentation or memory. No real financial data, vendor names, or
amounts from that runtime data are reproduced in this document. Cost-of-time-
and-money analysis is maintained privately.*
