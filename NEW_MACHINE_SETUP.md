# New-Machine Setup — Claude Code per-project memory

How to restore the Claude Code **per-project memory** system on a fresh machine.

## What this system is

Each project has a dedicated memory store at `~/.claude/projects/<encoded-path>/memory/`, which is its **own git repo** pushed to a private `github.com/wegofwd2020-hub/<name>-memory` remote. A single global **`Stop` hook** in `~/.claude/settings.json` auto-commits and pushes that store after every response turn. Top-level `_claude-memory-<project>` **symlinks** expose each store in the workspace for browsing.

> The remotes are the source of truth. On a new machine you (1) recreate the hook, (2) clone each memory repo into the matching encoded path, (3) recreate the symlinks.

## Prerequisites

- Claude Code installed (creates `~/.claude/`).
- `git` and the GitHub CLI `gh`, authenticated as the repo owner: `gh auth login` (account `wegofwd2020-hub`).
- The project repos themselves cloned to the **same absolute paths** as the old machine (the encoded path is derived from the absolute path — see *Path dependency* below).

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

## Step 2 + 3 — Clone the memory repos and recreate the symlinks

Run this block (adjust `BASE` if your layout differs). It derives each encoded path, clones the repo into place, and makes the symlink.

```bash
set -e
GH="https://github.com/wegofwd2020-hub"
BASE="$HOME/Documents/code/projects/AIStuff"          # parent of STEM_studybuddy and dronePrjs
PROOT="$HOME/.claude/projects"
enc() { echo "$1" | sed 's|[/_]|-|g'; }

# project_abs_path | memory_repo | symlink_abs_path
MAP="
$BASE/STEM_studybuddy/StudyBuddy_OnDemand|studybuddy-memory|$BASE/STEM_studybuddy/_claude-memory-studybuddy
$BASE/STEM_studybuddy/StudyBuddy_SelfLearner|studybuddy-selflearner-memory|$BASE/STEM_studybuddy/_claude-memory-studybuddy-selflearner
$BASE/STEM_studybuddy/thittam|thittam-memory|$BASE/STEM_studybuddy/_claude-memory-thittam
$BASE/STEM_studybuddy/mambakkam-net|mambakkam-net-memory|$BASE/STEM_studybuddy/_claude-memory-mambakkam-net
$BASE/STEM_studybuddy/project-critique|project-critique-memory|$BASE/STEM_studybuddy/_claude-memory-project-critique
$BASE/STEM_studybuddy/MarketingTools|MarketingTools-memory|$BASE/STEM_studybuddy/_claude-memory-MarketingTools
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
  [ -e "$sym" ] || ln -s "$M" "$sym"
done
```

## Verify

```bash
PROOT="$HOME/.claude/projects"
for enc in \
  -home-*-StudyBuddy-OnDemand -home-*-StudyBuddy-SelfLearner -home-*-thittam \
  -home-*-mambakkam-net -home-*-project-critique -home-*-MarketingTools \
  -home-*-AIStuff-dronePrjs -home-*-AIStuff-dronePrjs-closedSpace ; do
  for M in "$PROOT"/$enc/memory; do
    [ -d "$M/.git" ] && echo "OK  $(git -C "$M" log -1 --format='%h %s')  <- $M"
  done
done
```

Each should show its latest commit, and `git -C <M> status` should be clean. From then on the Stop hook resumes auto-snapshotting.

## The eight repos

| Project | Memory repo | Symlink |
|---|---|---|
| studybuddy (StudyBuddy_OnDemand) | `studybuddy-memory` | `STEM_studybuddy/_claude-memory-studybuddy` |
| studybuddy-selflearner | `studybuddy-selflearner-memory` | `STEM_studybuddy/_claude-memory-studybuddy-selflearner` |
| thittam | `thittam-memory` | `STEM_studybuddy/_claude-memory-thittam` |
| mambakkam-net | `mambakkam-net-memory` | `STEM_studybuddy/_claude-memory-mambakkam-net` |
| project-critique | `project-critique-memory` | `STEM_studybuddy/_claude-memory-project-critique` |
| MarketingTools | `MarketingTools-memory` | `STEM_studybuddy/_claude-memory-MarketingTools` |
| dronePrjs | `dronePrjs-memory` | `AIStuff/_claude-memory-dronePrjs` |
| closedSpace (subdir of dronePrjs) | `closedSpace-memory` | `AIStuff/_claude-memory-closedSpace` |

## Path dependency (important)

The encoded path is derived from the project's **absolute path**. If the new machine uses a different username or layout (e.g. `/home/otheruser/...` or a different folder structure), the encoded dir name changes and the hook will look in a *different* place. Either (a) replicate the same absolute paths, or (b) clone each memory repo into the encoded path the new layout produces (recompute with the `enc()` helper above). The symlink targets are absolute too, so regenerate them with the block above rather than copying them verbatim.

## Adding a new project later

```bash
gh repo create wegofwd2020-hub/<name>-memory --private
M="$HOME/.claude/projects/$(echo /abs/path/to/project | sed 's|[/_]|-|g')/memory"
mkdir -p "$M" && : > "$M/MEMORY.md"
git -C "$M" init -b main && git -C "$M" remote add origin https://github.com/wegofwd2020-hub/<name>-memory.git
git -C "$M" add -A && git -C "$M" commit -m "chore: initial snapshot of Claude memory" && git -C "$M" push -u origin main
ln -s "$M" /workspace/parent/_claude-memory-<name>
```

The global Stop hook needs no change — it just needs the repo + remote to exist.
