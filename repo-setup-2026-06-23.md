# Repo / memory-sync setup work — 2026-06-23

Session log of operational changes to the per-project repo + Claude-memory sync
system. Companion to [`NEW_MACHINE_SETUP.md`](NEW_MACHINE_SETUP.md) (the living
how-to) and the runnable scripts `github_checkout.sh` / `github_update.sh`.

## Context

Hub layout on this machine is **not** the flat `~/Documents/AIStuff/wegofwd2020-hub/`
that `NEW_MACHINE_SETUP.md` still describes — it is:

```
~/Documents/code/projects/AIStuff/STEM_studybuddy/   <- the hub (BASE)
  ├── project-critique/        (this repo — holds the sync scripts + ops docs)
  ├── StudyBuddy_OnDemand/  Mentible/  thittam/  mambakkam-net/
  ├── pramana/  kathai-chithiram/  MarketingTools/  wegofwd-llm/
  ├── wegofwd-orchestration/   (NEW this session)
  └── dronePrjs/  (+ dronePrjs/closedSpace subdir)
```

Both scripts now derive `BASE` as the **parent of the current working dir**, so
they work regardless of where the hub lives — but must be run from inside a
project repo (a direct child of the hub).

## What changed

### 1. Script edits (committed to project-critique)
- **`github_checkout.sh` / `github_update.sh`**: registered the new
  `wegofwd-orchestration` project + memory repo in both repo lists.
- **`github_update.sh`**: now `git fetch --prune`s each repo first, and when a
  branch's upstream was deleted on the remote (e.g. a merged-and-deleted PR
  branch) it reports `MERGED` (HEAD already in `<remote>/main` → switch to main)
  or `ORPHANED` (gone and **not** in main) instead of a hard `ERROR`.
- **`github_checkout.sh`**: corrected the stale `# gh not installed here`
  comment — `gh` 2.45.0 is installed and authed on this machine; cloning still
  uses SSH by choice.

### 2. New repo: wegofwd-orchestration
- Created both `wegofwd2020-hub/wegofwd-orchestration` (project) and
  `wegofwd2020-hub/wegofwd-orchestration-memory` as **private** repos via `gh`.
- Seeded each with an initial commit on `main` (empty repos have no branch, which
  made `pull --ff-only` error): a `MEMORY.md` stub for the memory repo, a
  placeholder `README.md` for the project repo.
- The full orchestration toolkit was subsequently built on top of that init
  commit and pushed (separate from this infra work); it now syncs normally.

### 3. Fixed Mentible-memory divergence
- The repo was `ahead 8 / behind 1`: 8 local Stop-hook auto-snapshots vs. a
  remote `chore(memory): back up local memory` commit that had truncated
  `MEMORY.md` to a single line and deleted 3 files that were current locally.
- Resolved with a **union merge** (not a force-push): kept all 31 local entries
  and all 3 files, grafted in the remote-only `trust-manifest-workstream.md` +
  its index line. `MEMORY.md` went 31 → 32 entries. **Nothing lost from either
  side.** Merge commit pushed cleanly.
- Root cause = the Stop-hook auto-push racing a second session's push. If it
  recurs, add a `fetch + rebase` before the push in the hook.

### 4. Cloned previously-missing repos
- `dronePrjs-memory` and `closedSpace-memory` had been skipped by an earlier
  `set -e` abort (see below) — cloned + symlinked both.
- Cloned the `dronePrjs` **project** repo into the hub (`github_checkout.sh` only
  clones *memory* repos, never project repos). `closedSpace` is a plain subdir of
  dronePrjs, not its own code repo — but it has its own memory repo, which is how
  the scripts treat it.

### 5. Cleaned up StudyBuddy_OnDemand (was DIRTY)
- All untracked, no tracked edits. Committed the real deliverable
  `docs/VALIDATION_Feedback_06_14_2026.md`; gitignored editor/scratch cruft
  (`.obsidian/`, `docs/Untitled.base`, `sample_data_file.txt`).

## Gotcha worth remembering

`github_checkout.sh` uses `set -e`, so a single non-existent remote (the
not-yet-created `wegofwd-orchestration-memory`) **aborted the whole loop**,
silently skipping every repo after it in the list (dronePrjs/closedSpace). If a
new project is registered before its GitHub repos exist, create the repos first —
or the checkout will half-complete.

## End state

`github_update.sh` reports **every repo `up-to-date`** — 11 project repos and 12
memory repos, no `DIRTY` / `MISSING` / `ERROR` / `ORPHANED` lines.

## Follow-ups (not done)

- **`NEW_MACHINE_SETUP.md` is stale**: still says "eleven repos", flat
  `BASE=~/Documents/AIStuff/wegofwd2020-hub`, and its embedded `github_checkout.sh`
  copy lacks `wegofwd-orchestration` + the parent-of-CWD `BASE`. Reconcile it with
  the current scripts and the 12-repo reality.
