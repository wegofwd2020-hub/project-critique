# Weekly Doc Digest — Design

| Field | Value |
|---|---|
| Topic | Weekly documentation-change digest across 10 portfolio projects |
| Date | 2026-08-05 |
| Status | Approved (brainstorming) → ready for implementation plan |
| Owner | Sivakumar Mambakkam |
| Home | `project-critique/doc_digest/` (new standalone tool) |

## 1. Purpose

Produce a **weekly digest of what documentation changed** across a fixed set of 10 portfolio projects, so the operator can see — in one committed report — which docs were added/edited in the last 7 days and decide what to review. It is a **"what changed this week" feed**, not a staleness/drift alarm and not a code-review tool.

The digest is a **read-only observer**: it reads each repo's git history and writes a report into `project-critique`. It never moves, edits, or restructures any documentation, and never commits into a watched repo. Document locations stay exactly as they are today.

## 2. Scope

**In scope:** the 10 projects below, their doc-change activity over a rolling 7-day window, a committed markdown + HTML report on a weekly cron.

**Out of scope:** relocating docs (a separate, deferred item — moving Mentible's ~8 MB of decks to LFS/private-docs); email/push delivery; editing or generating doc content; watching the separate/mirror docs repos (`thittam_docs`, `studybuddy-docs`).

## 3. Key decisions (from brainstorming)

1. **Signal:** weekly digest of *what changed* (not drift, not staleness, not yes/no heartbeat).
2. **Delivery:** committed report file (markdown + HTML) in `project-critique`, beside `portfolio.html`. No new credentials.
3. **Doc locations are heterogeneous** — some projects keep docs in an in-repo `docs/` subfolder, two also have a separate lagging docs repo. Resolved to a **per-project doc-path map** in config.
4. **Dual-location projects** (`thittam`, `StudyBuddy_OnDemand`): watch the **active in-repo `docs/`** (where doc work happens); ignore the lagging mirror repos (`thittam_docs`, `studybuddy-docs`).
5. **SDD docs (`superpowers/`): two-tier, do NOT exclude.** Measured churn (last 7 days): Mentible superpowers 42 vs other 2; thittam 14 vs 3; StudyBuddy_OnDemand 10 vs 0. Excluding would make the busiest projects falsely read "no changes"; including flat would bury real docs. So: **headline docs listed by name; `superpowers/**` collapsed to a per-project count.**
6. **Architecture:** standalone Python tool (Approach A), not an extension of `portfolio_health` and not a shell script — the per-project map + two-tier grouping + render deserve tests and a clean boundary, and the weekly cadence shouldn't tangle into the daily health job.

## 4. Doc-path map (the config the digest reads)

Discovered on disk 2026-08-05:

| Project | Doc home (git pathspecs) | Notes |
|---|---|---|
| Mentible | `docs`, `Plans` | in-repo subfolder (214 md) |
| thittam | `docs` | in-repo active; `thittam_docs` mirror lags (ignored) |
| StudyBuddy_OnDemand | `docs` | in-repo active; `studybuddy-docs` mirror lags (ignored) |
| pramana | `docs` | in-repo subfolder |
| kathai-chithiram | `docs` | in-repo subfolder |
| atri-sangam | `docs` | in-repo subfolder |
| mambakkam-net | `docs` | in-repo subfolder (repo dir is `mambakkam-net`) |
| wegofwd-llm | `README.md`, `docs` | sparse (3 md) |
| wegofwd-video | `README.md` | README-only, no `docs/` |
| dronePrjs | `CLAUDE.md`, `closedSpace/docs` | non-standard (docs nested in subproject) |

## 5. Architecture & layout

Standalone tool beside `portfolio_health/`, one responsibility per file, **stdlib only** (`tomllib`, `subprocess`, `html`) — requires **Python 3.11+** for `tomllib` (matches the `portfolio_health` venv):

```
project-critique/
  doc_digest/
    doc_digest/
      config.py     # load+validate toml map; expand ~; defaults
      gitlog.py     # thin git subprocess helpers (log over pathspecs, in-window)
      collect.py    # per-project: changed doc files in the N-day window
      classify.py   # split each changed file → headline tier vs SDD tier
      render.py     # markdown + self-contained HTML (pure data→string)
      cli.py        # argparse: --config --since-days --as-of --base --out-html --out-md
    config/doc-digest.toml     # the 10-project doc-path map
    scripts/digest.sh          # weekly cron wrapper (guarded fetch → run → commit+rebase-push)
    tests/{test_config,test_collect,test_classify,test_render}.py
  doc-digest.html              # latest digest (committed; sits beside portfolio.html)
  doc-digest/YYYY-MM-DD.md     # dated archive
```

`collect`/`classify` are pure over `git log` output; `render` is pure data→string. Naming: `doc_digest/` = tool code; `doc-digest.html` + `doc-digest/` = generated output; the watched repos' docs are untouched.

### Config format (`doc-digest.toml`)

```toml
base      = "~/Documents/code/projects/AIStuff/STEM_studybuddy"   # hub; --base overrides
exclude   = ["**/node_modules/**", "**/.venv/**", "**/dist/**", "*-wt/**"]
sdd_globs = ["docs/superpowers/**"]        # matched → collapsed "SDD activity" tier
doc_exts  = [".md", ".txt", ".rst"]        # only these count as documents

[[project]]
name = "Mentible"
include = ["docs", "Plans"]
# … one [[project]] per row in §4; include = git pathspecs (dirs or files)
```

The map lives in config, not code — adding a project or fixing a path is a one-line edit.

## 6. Core pipeline (data flow)

Pure function of git history + a window. **No state file** — idempotent, re-runnable.

```
as_of (default now) ; since = as_of − N days (default 7)
for each project:
   git -C <repo> log --since=<since> --until=<as_of>
       --name-status --pretty='%H%x00%cI%x00%s'  -- <include pathspecs>
   → parse commits → per changed file: {path, change(A/M/D), commits, last_date}
   → drop files whose ext ∉ doc_exts, or matching `exclude`
   → classify: path matches sdd_globs → SDD tier ; else → headline tier
   → aggregate: headline = [files listed] ; sdd = {file_count, commit_count}
→ digest = {window, generated_at, projects:[…], totals}
```

`--name-status` yields add/modify/delete per file; dedup across commits keeps the latest change type + a commit count. Window is explicit ISO (`--since`/`--until`) so tests are deterministic via `--as-of`.

## 7. Output format

**Markdown** (`doc-digest/YYYY-MM-DD.md`): header (window + generated time + tallies), a summary table, then per-project details.

```
# Weekly Doc Digest — 2026-08-10   (window: 2026-08-03 → 2026-08-10)
_Generated 2026-08-10 07:45 · 10 projects · 4 with headline changes · 3 quiet · 0 errors_

| Project | Headline docs | SDD activity |
|---|---|---|
| Mentible | ADR-039 (M), STATUS.md (M) | 42 files / 18 commits |
| thittam | authz-plan.md (A) | 14 / 9 |
| StudyBuddy_OnDemand | — | 10 / 4 |
| pramana | mvp.md (M) | — |
| dronePrjs | MISSING (not cloned) | |

## Details
### Mentible — 2 headline, 42 SDD
- `docs/adr/ADR-039-x.md` — modified, 2 commits, last 08-08
- `docs/STATUS.md` — modified, last 08-09
```

**HTML** (`doc-digest.html`): self-contained, theme-aware CSS matching `portfolio.html`, A/M/D badges, quiet rows muted, MISSING/ERROR flagged. Rendered from the same digest object so md and html never disagree.

**Ordering:** headline-changed projects first (most changes on top), then SDD-only, then quiet, then MISSING/ERROR — the review signal floats to the top.

## 8. Scheduling & git

- **Cron:** `45 7 * * 1` — Monday 07:45 local, 15 min after the daily portfolio `refresh.sh` (07:30) has pulled all repos.
- **`digest.sh` wrapper** (mirrors the hardened `refresh.sh`):
  1. Guarded fetch of the 10 repos (ff-only, skip dirty/detached/non-github) — self-sufficient even if the daily pull didn't run.
  2. Run the CLI → write `doc-digest.html` + `doc-digest/<date>.md`.
  3. If output changed: commit + **`pull --rebase` before push**, abort-and-skip on true conflict.
  4. Log to `~/.local/share/doc-digest/digest.log`.
- The digest **reads** the 10 repos but **writes only** inside `project-critique`; never commits into a watched repo.

## 9. Error handling & edge cases

| Case | Behavior |
|------|----------|
| Repo not cloned | Row `MISSING (run github_checkout.sh)`; digest continues |
| Repo dirty / detached HEAD | Fine — `git log` reads history, not worktree |
| `git log` fails for a repo | Per-project `ERROR` row with message; others unaffected |
| No doc changes in window | Row `— no changes`; digest still generated |
| Bad include path / config typo | Pathspec yields nothing; validated at load where possible, logged |
| Config missing/malformed | Hard fail with a clear message |
| Empty week across all 10 | Valid digest ("0 headline changes"), still committed as the record |

No partial failure halts the run — one bad repo never blanks the digest.

## 10. Testing

Deterministic, no network. Unit tests build **temp git repos** and stamp commit dates via `GIT_COMMITTER_DATE`/`GIT_AUTHOR_DATE`, asserting against a fixed `--as-of`:

- **test_collect** — in-window file caught; out-of-window ignored; A/M/D captured; multi-commit dedup → latest type + commit count; non-doc ext dropped.
- **test_classify** — `docs/superpowers/**` → SDD; `docs/adr/…` → headline; `exclude` globs removed.
- **test_config** — toml loads, `~` expands, required fields validated, per-project include parsed.
- **test_render** — digest object → md/html shape; headline-first ordering; MISSING/ERROR/quiet rows; two-tier counts correct.

Coverage floor consistent with `portfolio_health`; pristine test output.

## 11. Definition of done

- `doc_digest` tool + config map + `digest.sh` committed to `project-critique`.
- Unit tests green; coverage at floor; output pristine.
- One manual run produces a correct `doc-digest.html` + dated markdown for the current window.
- Weekly cron installed (`45 7 * * 1`), logging to `~/.local/share/doc-digest/digest.log`.
- `github_checkout.sh` / `github_update.sh` unaffected (digest reads repos already managed there).
