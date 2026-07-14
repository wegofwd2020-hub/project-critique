# New-Machine Setup — Claude Code per-project memory

How to restore the Claude Code **per-project memory** system on a fresh machine.

## What this system is

Each project has a dedicated memory store at `~/.claude/projects/<encoded-path>/memory/`, which is its **own git repo** pushed to a private `github.com/wegofwd2020-hub/<name>-memory` remote. A single global **`Stop` hook** in `~/.claude/settings.json` auto-commits and pushes that store after every response turn. Top-level `_claude-memory-<project>` **symlinks** expose each store in the workspace for browsing.

> The remotes are the source of truth. On a new machine you (1) recreate the hook, (2) clone each memory repo into the matching encoded path, (3) recreate the symlinks.

## Prerequisites

- Claude Code installed (creates `~/.claude/`).
- `git`, plus **SSH access to GitHub** for the `wegofwd2020-hub` account (`ssh -T git@github.com` should greet you). The clone script uses SSH by default. `gh` (the GitHub CLI) is installed and authed on the current machine, so if you prefer HTTPS just run `gh auth login` and set `GH="https://github.com/wegofwd2020-hub"` in the script.
- The project repos cloned somewhere under a single **hub** folder (the encoded path is derived from each project's absolute path — see *Path dependency* below). The scripts no longer hardcode the hub location: they derive it as the **parent of the current working directory**, so run them from inside a project repo. On the current machine the hub is `~/Documents/code/projects/AIStuff/STEM_studybuddy/` and every project is a direct child of it.

## The encoding rule

`<encoded-path>` = the project's absolute path with every `/` **and** `_` replaced by `-`:

```bash
echo "$PWD" | sed 's|[/_]|-|g'
# /home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/thittam
#  -> -home-sivam-Documents-code-projects-AIStuff-STEM-studybuddy-thittam
```

This is the exact transform the hook uses, so the memory dir must sit under that name for the hook to find it.

## Step 1 — Recreate the global Stop hook

Add this to `~/.claude/settings.json` (merge into existing `hooks`):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "M=\"$HOME/.claude/projects/$(echo \"$PWD\" | sed 's|[/_]|-|g')/memory\"; [ -d \"$M/.git\" ] || exit 0; git -C \"$M\" add -A 2>/dev/null; if ! git -C \"$M\" diff --cached --quiet 2>/dev/null; then git -C \"$M\" commit -m \"auto: memory snapshot $(date -u +%Y-%m-%dT%H:%MZ)\" >/dev/null 2>&1 && git -C \"$M\" push origin main >/dev/null 2>&1; fi; exit 0",
            "timeout": 30,
            "async": true
          }
        ]
      }
    ]
  }
}
```

It is a no-op for any project whose memory dir isn't a git repo, so it's safe globally.

## Step 2 + 3 — Clone the project + memory repos and recreate the symlinks

Run this block (adjust `BASE` if your layout differs). It clones each project code repo flat under the hub, then derives each encoded path, clones the matching memory repo into place, and makes the symlink.

> This block is kept in sync with the runnable script `github_checkout.sh`, version-controlled in this repo. It derives the hub as the parent of CWD, so run it directly from inside a project repo (e.g. `cd <hub>/project-critique && sh github_checkout.sh`) — there is no longer a separate copy at the hub root. Keep this embedded block in sync with the script when you edit either.

```bash
#!/bin/sh
set -e
GH="git@github.com:wegofwd2020-hub"                     # clone over SSH (gh CLI is installed+authed if you prefer HTTPS)
BASE="$(dirname "$PWD")"                                # hub = parent of CWD; run from inside a project repo
PROOT="$HOME/.claude/projects"
enc() { echo "$1" | sed 's|[/_]|-|g'; }

# Project code repos cloned flat under the hub ($BASE/<name>). The GitHub repo name
# matches the local dir name for every project. closedSpace is a subdir of dronePrjs,
# not its own repo, so it is not listed here. wegofwd-video, wegofwd-expenses, and
# wegofwd-secure ARE project repos but have no memory repo, so they appear in PROJECTS
# below but NOT in the MAP. Keep this list in sync with PROJECTS in github_update.sh.
PROJECTS="StudyBuddy_OnDemand Mentible thittam mambakkam-net pramana kathai-chithiram project-critique MarketingTools wegofwd-llm wegofwd-orchestration wegofwd-video wegofwd-expenses wegofwd-secure dronePrjs medtracker"

echo "Project repos:"
for n in $PROJECTS; do
  P="$BASE/$n"
  if [ -d "$P/.git" ]; then echo "skip (exists): $n"; else
    git clone "$GH/$n.git" "$P"
    echo "cloned: $n -> $P"
  fi
done

echo "Memory repos:"
# project_abs_path | memory_repo | symlink_abs_path
MAP="
$BASE/StudyBuddy_OnDemand|studybuddy-memory|$BASE/_claude-memory-studybuddy
$BASE/Mentible|mentible-memory|$BASE/_claude-memory-mentible
$BASE/thittam|thittam-memory|$BASE/_claude-memory-thittam
$BASE/mambakkam-net|mambakkam-net-memory|$BASE/_claude-memory-mambakkam-net
$BASE/pramana|pramana-memory|$BASE/_claude-memory-pramana
$BASE/kathai-chithiram|kathai-chithiram-memory|$BASE/_claude-memory-kathai-chithiram
$BASE/project-critique|project-critique-memory|$BASE/_claude-memory-project-critique
$BASE/MarketingTools|MarketingTools-memory|$BASE/_claude-memory-MarketingTools
$BASE/wegofwd-llm|wegofwd-llm-memory|$BASE/_claude-memory-wegofwd-llm
$BASE/wegofwd-orchestration|wegofwd-orchestration-memory|$BASE/_claude-memory-wegofwd-orchestration
$BASE/dronePrjs|dronePrjs-memory|$BASE/_claude-memory-dronePrjs
$BASE/dronePrjs/closedSpace|closedSpace-memory|$BASE/_claude-memory-closedSpace
$BASE/medtracker|medtracker-memory|$BASE/_claude-memory-medtracker
"

echo "$MAP" | while IFS='|' read -r proj repo sym; do
  [ -z "$proj" ] && continue
  M="$PROOT/$(enc "$proj")/memory"
  if [ -d "$M/.git" ]; then echo "skip (exists): $repo"; else
    mkdir -p "$(dirname "$M")"
    git clone "$GH/$repo.git" "$M"
    echo "cloned: $repo -> $M"
  fi
  mkdir -p "$(dirname "$sym")"          # ensure workspace parent exists (may precede project clone)
  [ -e "$sym" ] || ln -s "$M" "$sym"
done
```

> Verified end-to-end in a temp dir on 2026-06-01 (original 8 repos). Re-verified 2026-06-23 on this machine: all 12 memory repos clone over SSH and their symlinks resolve under the hub (now `~/Documents/code/projects/AIStuff/STEM_studybuddy/`, derived as the parent of CWD). The `mkdir -p` above is required — without it `ln` fails if the workspace parent dir isn't present yet. `medtracker-memory` (13th) was added 2026-07-14; its GitHub repo exists and its symlink resolves, but a clean-machine clone of it has not been re-run.
>
> ⚠ `set -e` gotcha: if a project is registered in the MAP before its `<name>-memory` GitHub repo exists, the failed clone aborts the **whole loop**, silently skipping every repo listed after it. Create the GitHub repo(s) first (see *Adding a new project later*).

## Verify

```bash
PROOT="$HOME/.claude/projects"
for enc in \
  -home-*-StudyBuddy-OnDemand -home-*-Mentible -home-*-thittam \
  -home-*-mambakkam-net -home-*-project-critique -home-*-MarketingTools \
  -home-*-pramana -home-*-wegofwd-llm -home-*-kathai-chithiram \
  -home-*-wegofwd-orchestration -home-*-medtracker \
  -home-*-STEM-studybuddy-dronePrjs -home-*-STEM-studybuddy-dronePrjs-closedSpace ; do
  for M in "$PROOT"/$enc/memory; do
    [ -d "$M/.git" ] && echo "OK  $(git -C "$M" log -1 --format='%h %s')  <- $M"
  done
done
```

Each should show its latest commit, and `git -C <M> status` should be clean. From then on the Stop hook resumes auto-snapshotting.

## Keeping repos in sync (any machine)

`github_checkout.sh` is the one-time bootstrap. For day-to-day syncing, run the companion **`github_update.sh`** (tracked in this repo). It is re-runnable and safe.

It derives the hub folder (`BASE`) as **one level above the current working directory**, so it works on any machine no matter where the hub lives — but that means you must **run it from inside a project repo** (a direct child of the hub):

```bash
cd <hub>/project-critique          # any direct child of the hub works
sh github_update.sh
```

For every project repo *and* memory repo it skips anything dirty (never clobbers local work), does a `git pull --ff-only` on the clean ones, and reports per-repo status (`up-to-date` / `UPDATED <range>` / `DIRTY` / `MISSING` / `ERROR`). `closedSpace` is pulled as a memory-only entry, since it is a subdir of `dronePrjs` rather than its own clone. A `MISSING` line means that repo hasn't been cloned yet — run `github_checkout.sh` first (it clones both the project code repos and the memory repos).

## The twelve memory repos

All symlinks live directly under the hub (`<hub>` = `~/Documents/code/projects/AIStuff/STEM_studybuddy/` on the current machine; the scripts derive it as the parent of CWD).

There are **twelve memory repos** but **twelve project code repos** — the two sets don't line up one-to-one: `closedSpace` has a memory repo but no project clone (it's a subdir of `dronePrjs`), and `wegofwd-video` is a project code repo with **no memory repo yet** (so it's absent from this table and from the checkout MAP).

| Project | Memory repo | Symlink |
|---|---|---|
| studybuddy (StudyBuddy_OnDemand) | `studybuddy-memory` | `<hub>/_claude-memory-studybuddy` |
| Mentible (formerly StudyBuddy_SelfLearner) | `mentible-memory` | `<hub>/_claude-memory-mentible` |
| thittam | `thittam-memory` | `<hub>/_claude-memory-thittam` |
| mambakkam-net | `mambakkam-net-memory` | `<hub>/_claude-memory-mambakkam-net` |
| pramana | `pramana-memory` | `<hub>/_claude-memory-pramana` |
| kathai-chithiram | `kathai-chithiram-memory` | `<hub>/_claude-memory-kathai-chithiram` |
| project-critique | `project-critique-memory` | `<hub>/_claude-memory-project-critique` |
| MarketingTools | `MarketingTools-memory` | `<hub>/_claude-memory-MarketingTools` |
| wegofwd-llm | `wegofwd-llm-memory` | `<hub>/_claude-memory-wegofwd-llm` |
| wegofwd-orchestration | `wegofwd-orchestration-memory` | `<hub>/_claude-memory-wegofwd-orchestration` |
| dronePrjs | `dronePrjs-memory` | `<hub>/_claude-memory-dronePrjs` |
| closedSpace (subdir of dronePrjs) | `closedSpace-memory` | `<hub>/_claude-memory-closedSpace` |

## Shared-library watch tokens (`PROJECT_CRITIQUE_PR_TOKEN`)

Unlike everything above, this is **not machine-local** — it's a **GitHub repo secret** set once per watched library, and it survives machine changes. It's documented here because it's the one piece of portfolio setup that isn't captured by cloning + the Stop hook, and a fresh operator won't otherwise know it exists.

Two shared libraries are under **top-level watch**: a GitHub Actions workflow in each library repo compares its HEAD to a baseline pointer in `project-critique` and, on any change, opens a dated watch-report PR **to `project-critique`**. To push a branch and open that PR cross-repo, each workflow needs a token with write access to `project-critique` (the default `GITHUB_TOKEN` is scoped to the running repo only):

| Watched repo | Workflow | Baseline pointer (in project-critique) | Secret needed |
|---|---|---|---|
| `wegofwd-llm` | `wegofwd-llm/.github/workflows/watch.yml` | `wegofwd-llm-last-reviewed.txt` | `PROJECT_CRITIQUE_PR_TOKEN` |
| `wegofwd-video` | `wegofwd-video/.github/workflows/watch.yml` | `wegofwd-video-last-reviewed.txt` | `PROJECT_CRITIQUE_PR_TOKEN` |

**One-time setup (do once for the org, add the secret to each repo):**

1. Create **one** fine-grained PAT at <https://github.com/settings/personal-access-tokens>:
   - **Resource owner:** `wegofwd2020-hub`; **Repository access:** only `wegofwd2020-hub/project-critique`
   - **Permissions:** `Contents` → Read and write, `Pull requests` → Read and write (Metadata read-only is automatic)
   - **Expiration:** a date you'll actually rotate at (e.g. 1 year)
2. Add it as a repo secret named **`PROJECT_CRITIQUE_PR_TOKEN`** on **each** watched repo (the secret is per-repo even though the token value is shared):
   - `https://github.com/wegofwd2020-hub/wegofwd-llm/settings/secrets/actions`
   - `https://github.com/wegofwd2020-hub/wegofwd-video/settings/secrets/actions`
3. Verify: in each repo, **Actions → `watch` → Run workflow → `main`**. With the baseline already at HEAD it should report *"✅ no change since baseline"* and open no PR. Until the secret exists, the `watch` run fails at the *Checkout project-critique* step with `Input required and not supplied: token` — that failure is the "token pending" signal, not a bug. (The sibling `ci.yml` needs no secret and runs independently.)

Full per-repo instructions and the manual fallback live in each library's `.watch/README.md`.

## Path dependency (important)

The encoded path is derived from the project's **absolute path**. If the new machine uses a different username or layout (e.g. `/home/otheruser/...` or a different folder structure), the encoded dir name changes and the hook will look in a *different* place. Either (a) replicate the same absolute paths, or (b) clone each memory repo into the encoded path the new layout produces (recompute with the `enc()` helper above). The symlink targets are absolute too, so regenerate them with the block above rather than copying them verbatim.

## Adding a new project later

```bash
BASE="$(dirname "$PWD")"                                 # run from inside a project repo, or set the hub path explicitly
gh repo create wegofwd2020-hub/<name>-memory --private   # gh is installed+authed; or create it in the GitHub UI
M="$HOME/.claude/projects/$(echo "$BASE/<name>" | sed 's|[/_]|-|g')/memory"
mkdir -p "$M" && : > "$M/MEMORY.md"
git -C "$M" init -b main && git -C "$M" remote add origin git@github.com:wegofwd2020-hub/<name>-memory.git
git -C "$M" add -A && git -C "$M" commit -m "chore: initial snapshot of Claude memory" && git -C "$M" push -u origin main
ln -s "$M" "$BASE/_claude-memory-<name>"
```

The global Stop hook needs no change — it just needs the repo + remote to exist.

A few things to also do when adding a project:

- **Register it in both scripts.** Add `<name>` to the `PROJECTS` list and the `$BASE/<name>|<name>-memory|...` row in the `MAP` in `github_checkout.sh`, and add `<name>` to the `PROJECTS` list (and the `MEM_PATHS` block) in `github_update.sh`. The project's GitHub repo name must match the local dir name `<name>`.
- **Create the GitHub repo(s) before running `github_checkout.sh`.** Because of the `set -e` gotcha above, a missing `<name>` or `<name>-memory` remote aborts the rest of the checkout loop. The snippet here creates the memory repo locally and pushes, so it sidesteps the empty-clone problem; if you instead create an empty repo and let the script clone it, seed it with an initial commit on `main` first (an empty repo has no branch, so `pull --ff-only` errors).
- **`github_checkout.sh` clones both the project code repo and its memory repo.** The project repo is cloned flat under the hub at `$BASE/<name>`; the memory repo into the encoded path. closedSpace is the one exception — it's a subdir of `dronePrjs`, so it has a memory repo but no project clone of its own.
