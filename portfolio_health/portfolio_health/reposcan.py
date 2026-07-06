"""Repo rigor signals from file presence — mirrors DOCUMENTATION_AUDIT logic."""

from __future__ import annotations

from pathlib import Path


def scan_repo(repo_dir: Path) -> dict:
    """Return RepoScan: has_tests / has_docs / has_license by file presence."""
    has_tests = (repo_dir / "tests").is_dir() or \
        any(repo_dir.rglob("test_*.py")) or any(repo_dir.rglob("*_test.py"))
    has_docs = (repo_dir / "docs").is_dir() or (repo_dir / "README.md").is_file()
    has_license = any(repo_dir.glob("LICENSE*"))
    return {"has_tests": bool(has_tests), "has_docs": bool(has_docs),
            "has_license": bool(has_license)}
