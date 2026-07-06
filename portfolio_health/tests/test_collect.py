import json, subprocess, os
from datetime import date
from pathlib import Path
from portfolio_health.collect import collect


def _make_repo(root, name, progress=None):
    r = root / name; (r / "docs").mkdir(parents=True)
    subprocess.run(["git", "-C", str(r), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.email", "t@t.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.name", "t"], check=True, capture_output=True)
    if progress is not None:
        (r / "docs" / "progress.json").write_text(json.dumps(progress))
    (r / "f").write_text("x")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    env = {**os.environ, "GIT_AUTHOR_DATE": "2026-07-01T12:00:00",
           "GIT_COMMITTER_DATE": "2026-07-01T12:00:00"}
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "i"], check=True, capture_output=True, env=env)
    return r


def test_collect_two_repos(tmp_path):
    _make_repo(tmp_path, "alpha", progress={
        "project": "Alpha", "stage": "late-build",
        "features": [{"name": "A", "status": "done"}, {"name": "B", "status": "pending"}]})
    _make_repo(tmp_path, "skipme")
    port = collect(tmp_path, exclude=["skipme"], exploratory_stages=["unknown"],
                   today=date(2026, 7, 6))
    assert port["summary"]["projects"] == 1
    p = port["projects"][0]
    assert p["project"] == "Alpha" and p["counts"]["done"] == 1
    assert p["source_kind"] == "progress" and p["health"]["status"] in {"green", "yellow", "red"}
    assert port["summary"]["features"]["total"] == 2


def test_repo_without_source_flagged(tmp_path):
    _make_repo(tmp_path, "beta")  # no progress.json, no manifest
    port = collect(tmp_path, exclude=[], exploratory_stages=["unknown"], today=date(2026, 7, 6))
    assert port["projects"][0]["source_kind"] == "none"
