from doc_digest.gitlog import changed_files, GitError
import pytest
from pathlib import Path

def test_in_window_changes_captured(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-08-04T09:00:00")
    gitrepo.commit({"docs/a.md": "2", "docs/b.md": "1"}, "2026-08-06T09:00:00")
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    paths = sorted(c.path for c in out)
    assert paths == ["docs/a.md", "docs/b.md"]        # only the 08-06 commit is in-window
    assert all(c.commit_iso.startswith("2026-08-06") for c in out)

def test_out_of_window_ignored(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-07-01T09:00:00")
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    assert out == []

def test_status_letter(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-08-06T09:00:00")   # A
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    assert out[0].status == "A"

def test_bad_repo_raises():
    with pytest.raises(GitError):
        changed_files(Path("/nonexistent/repo"), "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
