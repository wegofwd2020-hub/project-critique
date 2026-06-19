# New-Machine Setup — Claude Code per-project memory

How to restore the Claude Code **per-project memory** system on a fresh machine.

## What this system is

Each project has a dedicated memory store at `~/.claude/projects/<encoded-path>/memory/`, which is its **own git repo** pushed to a private `github.com/wegofwd2020-hub/<name>-memory` remote. A single global **`Stop` hook** in `~/.claude/settings.json` auto-commits and pushes that store after every response turn. Top-level `_claude-memory-<project>` **symlinks** expose each store in the workspace for browsing.

> The remotes are the source of truth. On a new machine you (1) recreate the hook, (2) clone each memory repo into the matching encoded path, (3) recreate the symlinks.

## Prerequisites

- Claude Code installed (creates `~/.claude/`).
- `git`, plus **SSH access to GitHub** for the `wegofwd2020-hub` account (`ssh -T git@github.com` should greet you). The clone script uses SSH because HTTPS needs a token or the `gh` CLI, which isn't assumed to be installed. If you prefer HTTPS+`gh`, run `gh auth login` and set `GH="https://github.com/wegofwd2020-hub"` in the script.
- The project repos themselves cloned to the **same absolute paths** as the old machine (the encoded path is derived from the absolute path — see *Path dependency* below). Current layout is **flat**: every project lives directly under `~/Documents/AIStuff/wegofwd2020-hub/`.

## The encoding rule

`<encoded-path>` = the project's absolute path with every `/` **and** `_` replaced by `-`:

```bash
echo "$PWD" | sed 's|[/_]|-|g'
# /home/sivam/Documents/AIStuff/wegofwd2020-hub/thittam
#  -> -home-sivam-Documents-AIStuff-wegofwd2020-hub-thittam
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

## Step 2 + 3 — Clone the memory repos and recreate the symlinks

Run this block (adjust `BASE` if your layout differs). It derives each encoded path, clones the repo into place, and makes the symlink.

> This block is kept in sync with the runnable script. The version-controlled copy lives in this repo at `github_checkout.sh`; on a working machine the runnable copy sits one level up at `~/Documents/AIStuff/github_checkout.sh` (outside any repo, since it operates on the whole hub). Keep the two in sync when you edit either.

```bash
#!/bin/sh
set -e
GH="git@github.com:wegofwd2020-hub"                     # SSH (HTTPS needs gh/token; gh not assumed installed)
BASE="$HOME/Documents/AIStuff/wegofwd2020-hub"          # flat: every project is $BASE/<project>
PROOT="$HOME/.claude/projects"
enc() { echo "$1" | sed 's|[/_]|-|g'; }

# project_abs_path | memory_repo | symlink_abs_path
MAP="
$BASE/StudyBuddy_OnDemand|studybuddy-memory|$BASE/_claude-memory-studybuddy
$BASE/StudyBuddy_SelfLearner|studybuddy-selflearner-memory|$BASE/_claude-memory-studybuddy-selflearner
$BASE/thittam|thittam-memory|$BASE/_claude-memory-thittam
$BASE/mambakkam-net|mambakkam-net-memory|$BASE/_claude-memory-mambakkam-net
$BASE/pramana|pramana-memory|$BASE/_claude-memory-pramana
$BASE/kathai-chithiram|kathai-chithiram-memory|$BASE/_claude-memory-kathai-chithiram
$BASE/project-critique|project-critique-memory|$BASE/_claude-memory-project-critique
$BASE/MarketingTools|MarketingTools-memory|$BASE/_claude-memory-MarketingTools
$BASE/wegofwd-llm|wegofwd-llm-memory|$BASE/_claude-memory-wegofwd-llm
$BASE/dronePrjs|dronePrjs-memory|$BASE/_claude-memory-dronePrjs
$BASE/dronePrjs/closedSpace|closedSpace-memory|$BASE/_claude-memory-closedSpace
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

> Verified end-to-end in a temp dir on 2026-06-01 (original 8 repos). Re-verified live on 2026-06-19 on this machine: all 11 repos clone over SSH and all 11 symlinks resolve under the flat `wegofwd2020-hub/` layout. The `mkdir -p` above is required — without it `ln` fails if the workspace parent dir isn't present yet.

## Verify

```bash
PROOT="$HOME/.claude/projects"
for enc in \
  -home-*-StudyBuddy-OnDemand -home-*-StudyBuddy-SelfLearner -home-*-thittam \
  -home-*-mambakkam-net -home-*-project-critique -home-*-MarketingTools \
  -home-*-pramana -home-*-wegofwd-llm -home-*-kathai-chithiram \
  -home-*-wegofwd2020-hub-dronePrjs -home-*-wegofwd2020-hub-dronePrjs-closedSpace ; do
  for M in "$PROOT"/$enc/memory; do
    [ -d "$M/.git" ] && echo "OK  $(git -C "$M" log -1 --format='%h %s')  <- $M"
  done
done
```

Each should show its latest commit, and `git -C <M> status` should be clean. From then on the Stop hook resumes auto-snapshotting.

## Keeping repos in sync (any machine)

`github_checkout.sh` is the one-time bootstrap. For day-to-day syncing, run the companion **`github_update.sh`** (tracked in this repo; a runnable copy sits at `~/Documents/AIStuff/github_update.sh`). It is re-runnable and safe.

It derives the hub folder (`BASE`) as **one level above the current working directory**, so it works on any machine no matter where the hub lives — but that means you must **run it from inside a project repo** (a direct child of the hub):

```bash
cd <hub>/project-critique          # any direct child of the hub works
sh github_update.sh                 # or: sh ~/Documents/AIStuff/github_update.sh
```

For every project repo *and* memory repo it skips anything dirty (never clobbers local work), does a `git pull --ff-only` on the clean ones, and reports per-repo status (`up-to-date` / `UPDATED <range>` / `DIRTY` / `MISSING` / `ERROR`). `closedSpace` is pulled as a memory-only entry, since it is a subdir of `dronePrjs` rather than its own clone. A `MISSING` line means that repo hasn't been cloned yet — run `github_checkout.sh` (and clone the project repo itself) first.

## The eleven repos

All symlinks live directly under `wegofwd2020-hub/` (flat layout).

| Project | Memory repo | Symlink |
|---|---|---|
| studybuddy (StudyBuddy_OnDemand) | `studybuddy-memory` | `wegofwd2020-hub/_claude-memory-studybuddy` |
| studybuddy-selflearner | `studybuddy-selflearner-memory` | `wegofwd2020-hub/_claude-memory-studybuddy-selflearner` |
| thittam | `thittam-memory` | `wegofwd2020-hub/_claude-memory-thittam` |
| mambakkam-net | `mambakkam-net-memory` | `wegofwd2020-hub/_claude-memory-mambakkam-net` |
| pramana | `pramana-memory` | `wegofwd2020-hub/_claude-memory-pramana` |
| kathai-chithiram | `kathai-chithiram-memory` | `wegofwd2020-hub/_claude-memory-kathai-chithiram` |
| project-critique | `project-critique-memory` | `wegofwd2020-hub/_claude-memory-project-critique` |
| MarketingTools | `MarketingTools-memory` | `wegofwd2020-hub/_claude-memory-MarketingTools` |
| wegofwd-llm | `wegofwd-llm-memory` | `wegofwd2020-hub/_claude-memory-wegofwd-llm` |
| dronePrjs | `dronePrjs-memory` | `wegofwd2020-hub/_claude-memory-dronePrjs` |
| closedSpace (subdir of dronePrjs) | `closedSpace-memory` | `wegofwd2020-hub/_claude-memory-closedSpace` |

## Path dependency (important)

The encoded path is derived from the project's **absolute path**. If the new machine uses a different username or layout (e.g. `/home/otheruser/...` or a different folder structure), the encoded dir name changes and the hook will look in a *different* place. Either (a) replicate the same absolute paths, or (b) clone each memory repo into the encoded path the new layout produces (recompute with the `enc()` helper above). The symlink targets are absolute too, so regenerate them with the block above rather than copying them verbatim.

## Adding a new project later

```bash
BASE="$HOME/Documents/AIStuff/wegofwd2020-hub"
gh repo create wegofwd2020-hub/<name>-memory --private   # or create it in the GitHub UI if gh isn't installed
M="$HOME/.claude/projects/$(echo "$BASE/<name>" | sed 's|[/_]|-|g')/memory"
mkdir -p "$M" && : > "$M/MEMORY.md"
git -C "$M" init -b main && git -C "$M" remote add origin git@github.com:wegofwd2020-hub/<name>-memory.git
git -C "$M" add -A && git -C "$M" commit -m "chore: initial snapshot of Claude memory" && git -C "$M" push -u origin main
ln -s "$M" "$BASE/_claude-memory-<name>"
```

The global Stop hook needs no change — it just needs the repo + remote to exist.
