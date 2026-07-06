#!/usr/bin/env bash
# Refresh the portfolio dashboard: pull repos, collect, commit the snapshot.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # project-critique
PORTFOLIO_ROOT="${PORTFOLIO_ROOT:-$HOME/Documents/code/projects/AIStuff/STEM_studybuddy}"
PY="${PYTHON:-$ROOT/portfolio_health/.venv/bin/python}"
[ -x "$PY" ] || PY=python3
"$PY" -m portfolio_health \
    --config "$ROOT/config/portfolio.toml" \
    --json "$ROOT/portfolio.json" \
    --html "$ROOT/portfolio.html" || exit 1
cd "$ROOT"
if ! git diff --quiet portfolio.json portfolio.html; then
  git add portfolio.json portfolio.html
  # cron runs headless with no ssh-agent, so disable SSH commit-signing and push
  # over HTTPS via the gh credential helper (both work non-interactively).
  git -c commit.gpgsign=false \
      commit -m "chore(portfolio): refresh health snapshot $(date -u +%Y-%m-%d)"
  git push https://github.com/wegofwd2020-hub/project-critique.git HEAD:main
fi
