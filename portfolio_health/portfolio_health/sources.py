"""Resolve a repo's feature list from the first available source:
docs/progress.json (from the repo's own generator) → project-status.yaml
(hand manifest) → none. Every source normalizes to the same Feature shape."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

_VALID = {"done", "in-progress", "pending"}


def feature_counts(features: list[dict]) -> dict:
    """Tally features by status. implemented = done + in-progress."""
    done = sum(1 for f in features if f.get("status") == "done")
    inprog = sum(1 for f in features if f.get("status") == "in-progress")
    pending = sum(1 for f in features if f.get("status") == "pending")
    return {"total": len(features), "done": done, "in_progress": inprog,
            "pending": pending, "implemented": done + inprog}


def _normalize(features: list, error_prefix: str) -> tuple[list[dict], str | None]:
    out, err = [], None
    for f in features or []:
        status = f.get("status")
        if status not in _VALID:
            err = f"{error_prefix}: feature {f.get('name')!r} has bad status {status!r}"
            continue
        out.append({"id": f.get("id"), "name": f.get("name", "(unnamed)"),
                    "status": status, "commits": f.get("commits")})
    return out, err


def resolve_source(repo_dir: Path) -> dict:
    """Return SourceResult for a repo, honoring the precedence."""
    pj = repo_dir / "docs" / "progress.json"
    if pj.is_file():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            feats, err = _normalize(data.get("features"), "progress.json")
            return {"kind": "progress", "stage": data.get("stage"),
                    "features": feats, "error": err}
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            return {"kind": "progress", "stage": None, "features": [],
                    "error": f"unreadable progress.json: {e}"}

    mf = repo_dir / "project-status.yaml"
    if mf.is_file():
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
            feats, err = _normalize(data.get("features"), "project-status.yaml")
            return {"kind": "manifest", "stage": data.get("stage"),
                    "features": feats, "error": err}
        except (OSError, yaml.YAMLError, AttributeError) as e:
            return {"kind": "manifest", "stage": None, "features": [],
                    "error": f"unreadable manifest: {e}"}

    return {"kind": "none", "stage": None, "features": [], "error": None}
