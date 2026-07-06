"""Discover git repos under the root and assemble the Portfolio record."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from portfolio_health.gitstats import git_stats
from portfolio_health.health import assess
from portfolio_health.reposcan import scan_repo
from portfolio_health.sources import feature_counts, resolve_source


def _iter_repos(root: Path, exclude: list[str]):
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in exclude or not (child / ".git").exists():
            continue
        yield child


def collect(root: Path, exclude: list[str], exploratory_stages: list[str],
            today: date | None = None) -> dict:
    """Scan every git repo under `root` (minus `exclude`) into a Portfolio."""
    root = Path(root).expanduser()
    today = today or datetime.now(timezone.utc).date()
    projects, health_tally = [], {"green": 0, "yellow": 0, "red": 0}
    totals = {"total": 0, "done": 0, "in_progress": 0, "pending": 0, "implemented": 0}

    for repo in _iter_repos(root, exclude):
        src = resolve_source(repo)
        counts = feature_counts(src["features"])
        git = git_stats(repo, today=today)
        rigor = scan_repo(repo)
        stage = src["stage"] or "unknown"
        health = assess(counts, git, rigor, stage, src["kind"], exploratory_stages)
        health_tally[health["status"]] += 1
        for k in totals:
            totals[k] += counts[k]
        projects.append({
            "project": src["project"] or repo.name, "stage": stage, "source_kind": src["kind"],
            "source_error": src["error"], "features": src["features"],
            "counts": counts, "git": git, "rigor": rigor, "health": health,
        })

    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "root": str(root),
            "projects": projects,
            "summary": {"projects": len(projects), "health": health_tally,
                        "features": totals}}
