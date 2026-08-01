#!/usr/bin/env bash
# Refresh the portfolio dashboard: pull repos, collect, commit the snapshot.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # project-critique
PORTFOLIO_ROOT="${PORTFOLIO_ROOT:-$HOME/Documents/code/projects/AIStuff/STEM_studybuddy}"
PY="${PYTHON:-$ROOT/portfolio_health/.venv/bin/python}"
[ -x "$PY" ] || PY=python3

# Guarded pull: refresh each repo's committed sources (progress.json, manifests)
# before scanning, WITHOUT ever disturbing local work. A repo is skipped (and
# scanned as-is) if it's dirty, on a detached HEAD, has no github origin, or the
# pull isn't a clean fast-forward. Pull over HTTPS (gh credential helper) even
# when origin is SSH, so it works headless in cron with no ssh-agent.
echo "--- $(date -Is) pulling sources ---"
for d in "$PORTFOLIO_ROOT"/*/; do
  name="$(basename "$d")"
  case "$name" in _claude-memory-*|project-critique) continue ;; esac  # scan-excluded / self
  [ -e "$d/.git" ] || continue
  if [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ]; then
    echo "  skip $name: uncommitted changes"; continue
  fi
  br="$(git -C "$d" symbolic-ref --quiet --short HEAD 2>/dev/null)" || { echo "  skip $name: detached HEAD"; continue; }
  url="$(git -C "$d" remote get-url origin 2>/dev/null)" || { echo "  skip $name: no origin"; continue; }
  https="$(printf '%s' "$url" | sed -E 's#^git@github\.com:#https://github.com/#')"
  case "$https" in https://github.com/*) ;; *) echo "  skip $name: non-github origin"; continue ;; esac
  if git -C "$d" pull --ff-only --quiet "$https" "$br" 2>/dev/null; then
    echo "  pulled $name ($br)"
  else
    echo "  skip $name: not a fast-forward"
  fi
done

"$PY" -m portfolio_health \
    --config "$ROOT/config/portfolio.toml" \
    --json "$ROOT/portfolio.json" \
    --html "$ROOT/portfolio.html" || exit 1
cd "$ROOT"
if ! git diff --quiet portfolio.json portfolio.html; then
  URL="https://github.com/wegofwd2020-hub/project-critique.git"
  git add portfolio.json portfolio.html
  # cron runs headless with no ssh-agent, so disable SSH commit-signing and push
  # over HTTPS via the gh credential helper (both work non-interactively).
  git -c commit.gpgsign=false \
      commit -m "chore(portfolio): refresh health snapshot $(date -u +%Y-%m-%d)"
  # Reconcile with anything pushed elsewhere (e.g. a critique from another
  # machine) BEFORE pushing, so a diverged remote doesn't silently reject the
  # push and let daily snapshots pile up unpushed. The snapshot touches only
  # the two generated artifacts, so a rebase almost never conflicts; on the
  # rare true conflict, abort and keep the commit local for the next run rather
  # than forcing over someone else's work.
  if ! git -c rebase.autoStash=false pull --rebase --quiet "$URL" main; then
    git rebase --abort 2>/dev/null || true
    echo "refresh: rebase conflict against origin/main — commit kept local, push skipped"
    exit 1
  fi
  git push "$URL" HEAD:main
fi
