import os
import subprocess
from portfolio_health.staleness import assess_staleness, reviewed_sha


def _git(r, *a, env=None):
    subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, env=env)


def _repo(tmp_path):
    r = tmp_path / "repo"; r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.com")
    _git(r, "config", "user.name", "t")
    return r


def _commit(r, msg):
    (r / "f.txt").write_text(msg)
    _git(r, "add", ".")
    env = {**os.environ, "GIT_AUTHOR_DATE": "2026-07-01T12:00:00",
           "GIT_COMMITTER_DATE": "2026-07-01T12:00:00"}
    _git(r, "commit", "-qm", msg, env=env)
    return subprocess.run(["git", "-C", str(r), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


# --- reviewed_sha ---

def test_reviewed_sha_reads_anchor(tmp_path):
    (tmp_path / "alpha-last-reviewed.txt").write_text("abc1234\n")
    assert reviewed_sha(tmp_path, "alpha") == "abc1234"


def test_reviewed_sha_missing_file_is_none(tmp_path):
    assert reviewed_sha(tmp_path, "nope") is None


def test_reviewed_sha_empty_file_is_none(tmp_path):
    (tmp_path / "beta-last-reviewed.txt").write_text("   \n")
    assert reviewed_sha(tmp_path, "beta") is None


def test_reviewed_sha_none_dir_is_none(tmp_path):
    assert reviewed_sha(None, "alpha") is None


# --- assess_staleness ---

def test_no_sha_is_unknown(tmp_path):
    r = _repo(tmp_path); _commit(r, "a")
    assert assess_staleness(r, None) == {
        "reviewed_sha": None, "commits_behind": None, "status": "unknown"}


def test_head_equals_reviewed_is_fresh(tmp_path):
    r = _repo(tmp_path); sha = _commit(r, "a")
    s = assess_staleness(r, sha)
    assert s == {"reviewed_sha": sha, "commits_behind": 0, "status": "fresh"}


def test_commits_ahead_is_stale(tmp_path):
    r = _repo(tmp_path); sha0 = _commit(r, "a"); _commit(r, "b"); _commit(r, "c")
    s = assess_staleness(r, sha0)
    assert s["status"] == "stale" and s["commits_behind"] == 2 and s["reviewed_sha"] == sha0


def test_unknown_sha_degrades_to_unknown(tmp_path):
    r = _repo(tmp_path); _commit(r, "a")
    s = assess_staleness(r, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    assert s["status"] == "unknown" and s["commits_behind"] is None
