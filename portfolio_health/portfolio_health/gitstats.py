"""Git activity signals for a repo, via the git CLI. Any failure (not a repo,
git missing) degrades to nulls — one bad repo never aborts the portfolio run."""

from __future__ import annotations

import subprocess
from datetime import date, datetime, timezone
from pathlib import Path


def _run(repo_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo_dir), *args],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def git_stats(repo_dir: Path, today: date | None = None) -> dict:
    """Return GitStats. `today` overrides the current date for age math (tests)."""
    null = {"commits_30d": None, "last_commit_age_days": None, "branch": None}
    if _run(repo_dir, "rev-parse", "--is-inside-work-tree") != "true":
        return null
    branch = _run(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    count = _run(repo_dir, "rev-list", "--count", "--since=30.days", "HEAD")
    ts = _run(repo_dir, "log", "-1", "--format=%ct")
    age = None
    if ts and ts.isdigit():
        commit_day = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        age = ((today or datetime.now(timezone.utc).date()) - commit_day).days
    return {"commits_30d": int(count) if count and count.isdigit() else None,
            "last_commit_age_days": age, "branch": branch}
