import subprocess, pytest
from pathlib import Path

@pytest.fixture
def gitrepo(tmp_path):
    """A git repo you can add dated commits to.
    Usage: gitrepo.commit({"docs/a.md": "x"}, "2026-08-04T09:00:00")
    """
    root = tmp_path / "repo"; root.mkdir()
    def run(*args, when=None):
        env = None
        if when:
            import os
            env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True, text=True, env=env)
    run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
    class Repo:
        path = root
        def commit(self, files, when, msg="c", delete=None):
            for rel, body in files.items():
                f = root / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(body)
                run("add", rel)
            for rel in (delete or []):
                run("rm", "-q", rel)
            run("commit", "-q", "-m", msg, when=when)
    return Repo()
