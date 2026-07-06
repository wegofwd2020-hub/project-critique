"""Repo rigor signals from file presence — mirrors DOCUMENTATION_AUDIT logic."""

from __future__ import annotations

from pathlib import Path


def _safe_any(iterator) -> bool:
    """Safely iterate, returning True on first match; False on any OSError or empty."""
    try:
        for _ in iterator:
            return True
    except OSError:
        return False
    return False


def scan_repo(repo_dir: Path) -> dict:
    """Return RepoScan: has_tests / has_docs / has_license by file presence.

    Degrades gracefully on filesystem errors (OSError) — never raises or aborts.
    """
    try:
        has_tests = (repo_dir / "tests").is_dir() or \
            _safe_any(repo_dir.rglob("test_*.py")) or _safe_any(repo_dir.rglob("*_test.py"))
        has_docs = (repo_dir / "docs").is_dir() or (repo_dir / "README.md").is_file()
        has_license = _safe_any(repo_dir.glob("LICENSE*"))
    except OSError:
        return {"has_tests": False, "has_docs": False, "has_license": False}
    return {"has_tests": bool(has_tests), "has_docs": bool(has_docs),
            "has_license": bool(has_license)}
