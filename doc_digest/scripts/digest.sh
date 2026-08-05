#!/usr/bin/env bash
# digest.sh — weekly wrapper for the doc digest. Reads the 10 watched repos
# (read-only), writes the report into project-critique, commits + rebase-pushes.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"        # project-critique
# Hub holding the 10 watched repos. Default matches portfolio_health/refresh.sh
# (the sibling cron this runs beside, on the STEM_studybuddy machine). Override
# with PORTFOLIO_ROOT on any other machine — it controls both the fetch loop
# below AND the CLI's --base, so the two never drift.
BASE="${PORTFOLIO_ROOT:-$HOME/Documents/code/projects/AIStuff/STEM_studybuddy}"
PY="${PYTHON:-$ROOT/portfolio_health/.venv/bin/python}"; [ -x "$PY" ] || PY=python3
URL="https://github.com/wegofwd2020-hub/project-critique.git"
LOG_DIR="$HOME/.local/share/doc-digest"; mkdir -p "$LOG_DIR" "$ROOT/doc-digest"
DATE="$(date -u +%Y-%m-%d)"

# Guarded fetch of watched repos (ff-only; skip dirty/detached/non-github) so the
# digest is correct even if the daily portfolio refresh didn't run.
for name in Mentible thittam StudyBuddy_OnDemand pramana kathai-chithiram \
            atri-sangam mambakkam-net wegofwd-llm wegofwd-video dronePrjs; do
  d="$BASE/$name"; [ -e "$d/.git" ] || continue
  [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ] && continue
  br="$(git -C "$d" symbolic-ref --quiet --short HEAD 2>/dev/null)" || continue
  url="$(git -C "$d" remote get-url origin 2>/dev/null)" || continue
  https="$(printf '%s' "$url" | sed -E 's#^git@github\.com:#https://github.com/#')"
  case "$https" in https://github.com/*) git -C "$d" pull --ff-only --quiet "$https" "$br" 2>/dev/null || true ;; esac
done

PYTHONPATH="$ROOT/doc_digest" "$PY" -m doc_digest.cli \
    --config "$ROOT/doc_digest/config/doc-digest.toml" \
    --base "$BASE" \
    --as-of "$(date -Iseconds)" --since-days 7 \
    --out-md "$ROOT/doc-digest/$DATE.md" \
    --out-html "$ROOT/doc-digest.html" || exit 1

cd "$ROOT"
if ! git diff --quiet doc-digest.html "doc-digest/$DATE.md" 2>/dev/null || \
   [ -n "$(git status --porcelain "doc-digest/$DATE.md")" ]; then
  git add doc-digest.html "doc-digest/$DATE.md"
  git -c commit.gpgsign=false commit -m "chore(doc-digest): weekly digest $DATE"
  if ! git -c rebase.autoStash=false pull --rebase --quiet "$URL" main; then
    git rebase --abort 2>/dev/null || true
    echo "doc-digest: rebase conflict — commit kept local, push skipped"; exit 1
  fi
  git push "$URL" HEAD:main
fi
