# Design: Portfolio Health Dashboard

**Date:** 2026-07-06
**Status:** Approved — ready for implementation planning
**Owner:** Siva
**Home repo:** `project-critique` (the portfolio-analysis repo)

A committed, cron-refreshed dashboard that shows the health of every repo in the
portfolio at a glance — feature progress, activity, and rigor — so that as the
team grows past one person, status is explicit and shared instead of living in
the lead's head.

---

## 1. Problem & Goals

One founder has tracked project status mentally. Onboarding more people breaks
that: there is no shared, structured view of what each repo has built, what is
pending, who owns it, or whether a project is healthy or stalling.

**Goals:**
1. **One shared view** — per-repo feature counts (done / in-progress / pending), stage, owners, activity, and a health signal, generated from data anyone can see and edit.
2. **Explicit source of truth** — features/pending come from a git-tracked manifest each repo carries, not from anyone's memory.
3. **Auto-derived where possible** — git activity and repo rigor (tests/docs) are computed, not hand-maintained.
4. **Transparent health** — the health signal is a rule set with a shown reason, never a black box.
5. **Zero-friction consumption** — the team does `git pull` and opens one committed HTML file; the lead's cron refreshes it.

**Non-goals (v1):**
- **No token/cost usage.** Deferred to v2 (would parse `~/.claude/projects/` and is per-machine, so it belongs in a later pass). Designed for but not built.
- **No hosting / web server / auth.** Output is a self-contained committed HTML file + JSON.
- **No writing back to repos.** Read-only over the repos and git; the dashboard never mutates a tracked project.
- **No issue-tracker integration.** The manifest is the source; GitHub-issues ingestion is a possible v2.
- **No historical trend charts.** v1 is a current-state snapshot (each commit of `portfolio.json` is an implicit history; charts come later).

---

## 2. Architecture

A small Python tool in `project-critique/portfolio_health/`. A collector reads
each repo, builds a per-project record, and a renderer emits a self-contained
HTML dashboard. Both artifacts are committed to `project-critique`.

```
project-critique/
├── portfolio_health/
│   ├── manifest.py     # load + validate project-status.yaml
│   ├── gitstats.py     # commits/30d, last-commit age, current branch
│   ├── reposcan.py     # has tests? docs? LICENSE? (file presence)
│   ├── health.py       # rule-based 🟢/🟡/🔴 + reason from the signals above
│   ├── collect.py      # discover repos → assemble portfolio.json
│   ├── render.py       # portfolio.json → portfolio.html (self-contained)
│   ├── cli.py          # `portfolio-health` entry point
│   └── tests/
├── portfolio.json      # committed data snapshot (the machine-readable truth)
├── portfolio.html      # committed self-contained dashboard (team opens this)
└── config/portfolio.toml   # repos root + any per-repo overrides
```

**Runtime deps:** Python 3.11+, `PyYAML` (manifest parsing — the one non-stdlib
dep; YAML is chosen over TOML for human-friendly nested feature lists the team
edits by hand). Everything else is stdlib (`subprocess` for git, `json`, `html`).

**Repo discovery:** the collector scans the portfolio root (default
`~/Documents/code/projects/AIStuff/STEM_studybuddy`, configurable in
`portfolio.toml`) for git repositories. A repo **with** a `project-status.yaml`
contributes full metrics; a repo **without** one appears in the dashboard flagged
`no manifest` (a visible nudge to add one) with only its auto-derived signals.
This makes onboarding a repo = dropping in a manifest.

### Data flow

```
each repo dir ──▶ manifest.py (project-status.yaml → features/stage/owners)
              ├──▶ gitstats.py  (git log → commits/30d, last-commit age, branch)
              └──▶ reposcan.py  (fs → has_tests, has_docs, has_license)
                        │
                        ▼
                   health.py  (signals → status + reason)
                        │
                        ▼
              collect.py → portfolio.json ──▶ render.py → portfolio.html
```

---

## 3. Manifest — `project-status.yaml`

One file per repo, committed to that repo, maintained by its owners. Minimal and
human-first:

```yaml
project: StudyBuddy_OnDemand      # display name
stage: late-build                 # aligns with PORTFOLIO_SCORECARD stages
owners: [siva]                    # default owners for the repo
features:
  - name: School portal
    status: done                  # done | in-progress | pending
    owner: siva                   # optional; falls back to repo owners
  - name: Parent billing
    status: pending
    owner: alex
  - name: Offline sync
    status: in-progress
```

**Validation (`manifest.py`):**
- `project` (str, required), `stage` (str, optional — falls back to "unknown"),
  `owners` (list[str], optional), `features` (list, optional).
- Each feature: `name` (str, required), `status` ∈ {done, in-progress, pending}
  (required), `owner` (str, optional).
- Unknown status or missing required field → the manifest is reported as
  `invalid` in the dashboard with the specific error (never silently dropped),
  and the repo falls back to auto-derived signals only.

**Derived counts:** `features_total`, `done`, `in_progress`, `pending`;
`implemented = done + in_progress`.

---

## 4. Auto-derived signals

**`gitstats.py`** (via `git -C <repo>`), all wrapped so a non-repo or git error
degrades to nulls rather than aborting the run:
- `commits_30d` — `git log --since="30 days ago" --oneline | wc -l`
- `last_commit_age_days` — from `git log -1 --format=%ct`
- `branch` — `git rev-parse --abbrev-ref HEAD`

**`reposcan.py`** (file presence, mirroring `DOCUMENTATION_AUDIT.md` logic):
- `has_tests` — a `tests/` dir or any `test_*.py` / `*_test.*`
- `has_docs` — a `docs/` dir or `README.md`
- `has_license` — a `LICENSE*` file

---

## 5. Health status (transparent rule set)

Per project, compute a status ∈ {green, yellow, red} with a human-readable
`reason`. Rules are ordered; the first that fires sets the status. Weights/
thresholds live in `health.py` as named constants so they are tunable.

**Signals:** `progress = done / features_total` (None if no features);
`age = last_commit_age_days`; `rigor = has_tests + has_docs`.

```
RED   if age is not None and age > 30                → "dormant — no commits in {age}d"
RED   if progress is not None and progress < 0.25
        and stage in {late-build, shipped, active}    → "only {pct}% features done at {stage} stage"
RED   if manifest invalid or missing on a non-passion stage → "no valid status manifest"
YELLOW if age is not None and 14 < age <= 30          → "slowing — {age}d since last commit"
YELLOW if progress is not None and progress < 0.7     → "{pct}% features done"
YELLOW if rigor < 2                                    → "missing {tests/docs}"
GREEN  otherwise                                       → "active, {pct}% done, tests+docs"
```

Stages treated as "expecting rigor/progress" vs exploratory (passion/prototype)
are configurable so a passion repo isn't marked red for being early. The exact
constants are proposed here and owned by Siva to tune after first run.

---

## 6. Dashboard — `portfolio.html`

Self-contained HTML (no external resources, theme-aware, native `<details>`
roll-down + a live filter box), reusing the patterns proven in
`wegofwd-expenses/expenseweb`.

- **Top summary:** project count, health distribution (🟢 n · 🟡 n · 🔴 n),
  total features done / in-progress / pending across the portfolio.
- **Filter box:** live client-side filter by project, owner, stage, status.
- **Per project (row → roll-down):**
  - Summary row: health dot · project · stage · `done/in-progress/pending` ·
    commits/30d · last-active · owners.
  - Body (`<details>`): the feature list (name · status · owner), the derived
    signals (tests/docs/license, branch), and the health `reason`.
  - Repos with `no manifest` / `invalid` render with a clear badge and the
    auto-derived signals only.

`portfolio.json` is the machine-readable sibling (same data), committed so
diffs show status change over time and other tooling can consume it.

---

## 7. Orchestration

- `cli.py` → `portfolio-health --root <dir> --json <path> --html <path>`.
- A cron wrapper (lead's machine), mirroring the `wegofwd-expenses` cron pattern:
  `git pull` the portfolio repos → run the collector → write `portfolio.json` +
  `portfolio.html` → `git commit` + `git push` them in `project-critique`.
- Team members: `git pull` `project-critique` → open `portfolio.html`. They keep
  their repo's `project-status.yaml` current; the lead's cron reflects it.

---

## 8. Testing

- `pytest` per module; **no test touches the network or a real mailbox/remote**.
  git is exercised against tmp repos created in-test (`git init` + commits) or
  mocked; filesystem via `tmp_path`; manifests via fixture YAML.
- Cover: manifest validation (valid, invalid status, missing field, absent file);
  git stats on a tmp repo; reposcan presence/absence; each health rule branch;
  render self-containment + filter + roll-down; empty/`no manifest` portfolios.

---

## 9. Phasing

- **v1 (this spec):** collector (manifest + git + rigor + health) + renderer +
  committed `portfolio.json`/`portfolio.html` + cron. Seed `project-status.yaml`
  into the existing repos (bootstrapped from `PRODUCT_CATALOG.md` /
  `PORTFOLIO_SCORECARD.md` where possible, then owners refine).
- **v2 (design-for, don't build):** token/cost usage per project (parse
  `~/.claude/projects/` or `ccusage`); historical trend charts from the committed
  `portfolio.json` history; GitHub-issues ingestion as an alternative feature
  source; per-owner workload view.

---

## 10. Open items for Siva to tune after first run

- Health thresholds/weights in §5 (the age cutoffs, the progress bar, which
  stages "expect" rigor).
- The default portfolio root path and any repos to exclude, in `portfolio.toml`.
- Whether a repo with no manifest should be 🔴 or just badged (spec default:
  badged, and 🔴 only via the §5 stage rule).
