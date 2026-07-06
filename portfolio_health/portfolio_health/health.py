"""Transparent, ordered health rules → (status, reason). Thresholds are named
constants so they are easy to tune after the first real run."""

from __future__ import annotations

DORMANT_DAYS = 30
SLOWING_DAYS = 14
LOW_PROGRESS = 0.25    # below this at a serious stage → red
OK_PROGRESS = 0.70     # below this → yellow


def _progress(counts: dict) -> float | None:
    return counts["done"] / counts["total"] if counts["total"] else None


def assess(counts: dict, git: dict, rigor: dict, stage: str | None,
           source_kind: str, exploratory_stages: list[str]) -> dict:
    """Return Health. Rules are ordered; the first that fires wins."""
    stage = stage or "unknown"
    expects = stage not in exploratory_stages
    age = git.get("last_commit_age_days")
    prog = _progress(counts)
    pct = None if prog is None else round(prog * 100)

    if age is not None and age > DORMANT_DAYS:
        return {"status": "red", "reason": f"dormant — no commits in {age}d"}
    if prog is not None and prog < LOW_PROGRESS and expects:
        return {"status": "red", "reason": f"only {pct}% of features done at {stage} stage"}
    if source_kind == "none" and expects:
        return {"status": "red", "reason": "no status source (add progress.json or project-status.yaml)"}
    if age is not None and SLOWING_DAYS < age <= DORMANT_DAYS:
        return {"status": "yellow", "reason": f"slowing — {age}d since last commit"}
    if prog is not None and prog < OK_PROGRESS:
        return {"status": "yellow", "reason": f"{pct}% of features done"}
    missing = [k for k in ("tests", "docs") if not rigor.get(f"has_{k}")]
    if missing:
        return {"status": "yellow", "reason": f"missing {', '.join(missing)}"}
    tail = f"{pct}% done" if pct is not None else "no feature list"
    return {"status": "green", "reason": f"active, {tail}, tests+docs"}
