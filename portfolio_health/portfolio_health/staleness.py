"""How far a product has drifted past the commit its critique was last reviewed
at — the "is this critique stale?" signal.

The reviewed SHA lives in ``<reviewed_dir>/<repo_name>-last-reviewed.txt`` (the
same anchor convention the shared-library watches already use). Any git failure
or unknown SHA degrades to ``unknown`` — one bad repo never aborts the run
(mirrors :mod:`portfolio_health.gitstats`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def reviewed_sha(reviewed_dir: Path | None, repo_name: str) -> str | None:
    """Reviewed-at SHA for a repo, or None if there is no anchor file."""
    if reviewed_dir is None:
        return None
    try:
        text = (Path(reviewed_dir) / f"{repo_name}-last-reviewed.txt").read_text(
            encoding="utf-8")
    except OSError:
        return None
    parts = text.split()
    return parts[0] if parts else None


def _run(repo_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo_dir), *args],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def assess_staleness(repo_dir: Path, sha: str | None) -> dict:
    """Return Staleness: how many commits HEAD is ahead of the reviewed SHA.

    - ``fresh``   — HEAD is the reviewed commit (0 behind).
    - ``stale``   — HEAD has moved N commits past the reviewed commit.
    - ``unknown`` — no anchor, or the SHA/git could not be resolved.
    """
    if not sha:
        return {"reviewed_sha": None, "commits_behind": None, "status": "unknown"}
    count = _run(repo_dir, "rev-list", "--count", f"{sha}..HEAD")
    if count is None or not count.isdigit():
        return {"reviewed_sha": sha, "commits_behind": None, "status": "unknown"}
    n = int(count)
    return {"reviewed_sha": sha, "commits_behind": n,
            "status": "fresh" if n == 0 else "stale"}
