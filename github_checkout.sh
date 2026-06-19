#!/bin/sh
set -e
GH="git@github.com:wegofwd2020-hub"                     # SSH (HTTPS needs gh/token; gh not installed here)
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
