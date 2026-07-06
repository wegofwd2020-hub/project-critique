import subprocess
from datetime import date
from pathlib import Path
from portfolio_health.gitstats import git_stats


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _repo(tmp_path, commit_date="2026-06-01T12:00:00"):
    r = tmp_path / "r"; r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.com")
    _git(r, "config", "user.name", "t")
    (r / "f.txt").write_text("x")
    _git(r, "add", ".")
    import os
    env = {**os.environ, "GIT_AUTHOR_DATE": commit_date, "GIT_COMMITTER_DATE": commit_date}
    _git(r, "commit", "-qm", "init", env=env)
    return r


def test_stats_on_real_repo(tmp_path):
    r = _repo(tmp_path, "2026-06-20T12:00:00")
    s = git_stats(r, today=date(2026, 7, 6))
    assert s["last_commit_age_days"] == 16
    assert s["commits_30d"] == 1
    assert s["branch"] in ("main", "master")


def test_non_repo_degrades_to_nulls(tmp_path):
    s = git_stats(tmp_path / "not-a-repo", today=date(2026, 7, 6))
    assert s == {"commits_30d": None, "last_commit_age_days": None, "branch": None}
