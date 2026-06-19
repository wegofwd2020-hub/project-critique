#!/bin/sh
# github_update.sh — pull latest in every wegofwd2020-hub project repo and Claude memory repo.
# Companion to github_checkout.sh (one-time clone). Safe to re-run; never touches dirty repos.
#
#   - BASE (the hub folder) is derived as the parent of the current working directory, so this
#     works on any machine regardless of where the hub lives. RUN IT FROM INSIDE A PROJECT REPO
#     (a direct child of the hub), e.g.  cd <hub>/project-critique && sh github_update.sh
#   - Project repos live flat under $BASE/<project>.
#   - Memory repos live at $PROOT/<encoded project path>/memory (see the encoding rule in
#     NEW_MACHINE_SETUP.md). closedSpace is a subdir of dronePrjs, not its own clone, so it is
#     only pulled as a memory repo, not as a project repo.
set -u
BASE="$(dirname "$PWD")"          # one level above CWD = the hub folder
PROOT="$HOME/.claude/projects"
enc() { echo "$1" | sed 's|[/_]|-|g'; }

# project subdirs that are each their own git repo
PROJECTS="StudyBuddy_OnDemand StudyBuddy_SelfLearner thittam mambakkam-net pramana kathai-chithiram project-critique MarketingTools wegofwd-llm dronePrjs"

# absolute project paths whose memory repo should be pulled
MEM_PATHS="
$BASE/StudyBuddy_OnDemand
$BASE/StudyBuddy_SelfLearner
$BASE/thittam
$BASE/mambakkam-net
$BASE/pramana
$BASE/kathai-chithiram
$BASE/project-critique
$BASE/MarketingTools
$BASE/wegofwd-llm
$BASE/dronePrjs
$BASE/dronePrjs/closedSpace
"

upd() {  # $1 = repo dir, $2 = label
  d="$1"; label="$2"
  if [ ! -d "$d/.git" ]; then printf '  MISSING    %s  (run github_checkout.sh)\n' "$label"; return; fi
  if [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ]; then
    printf '  DIRTY      %s  (skipped — commit/stash first)\n' "$label"; return
  fi
  br=$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)
  out=$(git -C "$d" pull --ff-only 2>&1)
  if echo "$out" | grep -q 'Already up to date'; then
    printf '  up-to-date %s (%s)\n' "$label" "$br"
  elif echo "$out" | grep -qE 'Fast-forward|Updating'; then
    rng=$(echo "$out" | grep -oE '[0-9a-f]{7,}\.\.[0-9a-f]{7,}' | head -1)
    printf '  UPDATED    %s (%s) %s\n' "$label" "$br" "$rng"
  else
    printf '  ERROR      %s (%s): %s\n' "$label" "$br" "$(echo "$out" | tail -1)"
  fi
}

echo "Project repos:"
for n in $PROJECTS; do upd "$BASE/$n" "$n"; done

echo "Memory repos:"
echo "$MEM_PATHS" | while read -r p; do
  [ -z "$p" ] && continue
  upd "$PROOT/$(enc "$p")/memory" "$(basename "$p")-memory"
done
