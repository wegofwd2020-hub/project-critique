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
- **The collector is read-only.** It never mutates a tracked project at run time. (Separately and explicitly in scope: a one-time change to the two existing `generate_progress.py` scripts to *also* emit `docs/progress.json` — that is a deliverable, not the collector writing to repos.)
- **The dashboard does not poll GitHub issues directly.** Feature data comes from `progress.json` or `project-status.yaml`. thittam's generator already derives its progress from issues into `progress.json`; a general issue-tracker adapter is a possible v2.
- **No historical trend charts.** v1 is a current-state snapshot (each commit of `portfolio.json` is an implicit history; charts come later).

---

## 2. Architecture

A small Python tool in `project-critique/portfolio_health/`. A collector reads
each repo, resolves its **feature source** (see §3), builds a per-project record,
and a renderer emits a self-contained HTML dashboard. Both artifacts are
committed to `project-critique`.

```
project-critique/
├── portfolio_health/
│   ├── sources.py      # resolve a repo's feature source by precedence,
│   │                   #   normalize progress.json OR project-status.yaml → features
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

**Runtime deps:** Python 3.11+, `PyYAML` (only needed to parse the fallback
`project-status.yaml` manifest — YAML chosen over TOML for human-friendly nested
feature lists edited by hand). `progress.json` and everything else is stdlib
(`subprocess` for git, `json`, `html`).

**Repo discovery:** the collector scans the portfolio root (default
`~/Documents/code/projects/AIStuff/STEM_studybuddy`, configurable in
`portfolio.toml`) for git repositories. Each repo's feature data comes from the
first source that exists (§3); a repo with **no** source appears flagged
`no source` (a visible nudge) with only its auto-derived signals. Onboarding a
repo into the dashboard = it already has a progress generator, or someone drops
in a `project-status.yaml`.

### Data flow

```
each repo dir ──▶ sources.py   (docs/progress.json  → normalized features
              │                 else project-status.yaml → normalized features
              │                 else none)
              ├──▶ gitstats.py  (git log → commits/30d, last-commit age, branch)
              └──▶ reposcan.py  (fs → has_tests, has_docs, has_license)
                        │
                        ▼
                   health.py  (signals → status + reason)
                        │
                        ▼
              collect.py → portfolio.json ──▶ render.py → portfolio.html

(separately, in each epic/progress repo's own nightly GitHub Action:)
   generate_progress.py ──▶ docs/PROGRESS.md (as today)
                        └──▶ docs/progress.json (NEW — normalized feature list)
```

---

## 3. Feature sources (precedence)

A repo's feature data resolves from the **first** source that exists, all
normalized by `sources.py` to the same internal shape (a list of features, each
with `name` + `status ∈ {done, in-progress, pending}`):

1. **`docs/progress.json`** — emitted by the repo's own progress generator
   (StudyBuddy_OnDemand and thittam already run `generate_progress.py` nightly
   via GitHub Actions; they will be extended to also write this file). This is
   the richer, already-maintained source — the dashboard reuses it rather than
   asking those repos to duplicate their epics into a manifest.
2. **`project-status.yaml`** — the hand-maintained manifest, for repos that have
   **no** progress generator (most of the portfolio).
3. **none** — the repo shows with auto-derived signals only, flagged `no source`.

### 3a. `docs/progress.json` (normalized; produced by the generators)

The existing `generate_progress.py` already computes an epic/feature list with a
`**Status:**` line each; the change is to also dump it as JSON with the status
mapped to the three canonical values:

```json
{
  "project": "StudyBuddy_OnDemand",
  "generated": "2026-07-06T02:00:00Z",
  "source": "epics",
  "stage": "late-build",
  "features": [
    {"id": "Epic 1",  "name": "Multi-Provider LLM Pipeline", "status": "done",        "commits": 1},
    {"id": "Epic 6",  "name": "Platform Hardening",          "status": "in-progress", "commits": 1},
    {"id": "Epic 4",  "name": "Parent Portal",               "status": "pending",     "commits": 0}
  ]
}
```

**Status mapping** (from the epic emoji/text, in the generator): `✅` → `done`;
`🚧` → `in-progress`; `🔜` / `💭` / blank → `pending`. Each generator owns the
mapping for its own status vocabulary (thittam's issue/scope model maps its own
statuses to the same three values), so `progress.json` is uniform across repos
even though the human-facing `PROGRESS.md` layouts differ.

### 3b. `project-status.yaml` (manifest — fallback for repos without a generator)

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
RED   if no feature source (no progress.json / manifest) on a non-passion stage → "no status source"
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
- Cover: source precedence (progress.json wins over manifest over none);
  progress.json normalization + status mapping (✅/🚧/🔜/💭 → done/in-progress/pending);
  manifest validation (valid, invalid status, missing field, absent file);
  git stats on a tmp repo; reposcan presence/absence; each health rule branch;
  render self-containment + filter + roll-down; empty/`no source` portfolios.
- The generator change is tested in each repo's own suite: `generate_progress.py`
  emits a `progress.json` whose feature statuses match its `PROGRESS.md`.

---

## 9. Phasing

- **v1 (this spec):**
  - Collector (`sources.py` precedence + git + rigor + health) + renderer +
    committed `portfolio.json`/`portfolio.html` + cron.
  - **Extend the two existing generators** (`StudyBuddy_OnDemand/scripts/generate_progress.py`
    and `thittam/scripts/generate_progress.py`) to also emit `docs/progress.json`
    with the normalized status mapping (§3a). Their nightly GitHub Actions commit
    it. Keep `PROGRESS.md` unchanged.
  - Seed `project-status.yaml` into repos that have **no** generator
    (bootstrapped from `PRODUCT_CATALOG.md` / `PORTFOLIO_SCORECARD.md` where
    possible, then owners refine). Do NOT add a manifest to repos that emit
    `progress.json` — that would re-introduce the duplication this design avoids.
- **v2 (design-for, don't build):** token/cost usage per project (parse
  `~/.claude/projects/` or `ccusage`); historical trend charts from the committed
  `portfolio.json` history; GitHub-issues ingestion as an alternative feature
  source; per-owner workload view.

---

## 10. Open items for Siva to tune after first run

- Health thresholds/weights in §5 (the age cutoffs, the progress bar, which
  stages "expect" rigor).
- The default portfolio root path and any repos to exclude, in `portfolio.toml`.
- Whether a repo with no feature source should be 🔴 or just badged (spec
  default: badged, and 🔴 only via the §5 stage rule).
