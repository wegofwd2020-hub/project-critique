import json
from pathlib import Path
from portfolio_health.sources import resolve_source, feature_counts


def test_counts():
    feats = [{"status": "done"}, {"status": "done"}, {"status": "in-progress"},
             {"status": "pending"}]
    c = feature_counts(feats)
    assert c == {"total": 4, "done": 2, "in_progress": 1, "pending": 1, "implemented": 3}


def test_progress_json_wins(tmp_path):
    d = tmp_path / "docs"; d.mkdir()
    (d / "progress.json").write_text(json.dumps({
        "project": "X", "stage": "late-build", "source": "epics",
        "features": [{"id": "Epic 1", "name": "A", "status": "done", "commits": 3},
                     {"id": "Epic 2", "name": "B", "status": "pending"}]}))
    (tmp_path / "project-status.yaml").write_text("project: X\nfeatures: []\n")  # ignored
    r = resolve_source(tmp_path)
    assert r["kind"] == "progress" and r["stage"] == "late-build"
    assert len(r["features"]) == 2 and r["features"][0]["status"] == "done"


def test_manifest_fallback(tmp_path):
    (tmp_path / "project-status.yaml").write_text(
        "project: Y\nstage: prototype\nowners: [siva]\n"
        "features:\n  - name: F1\n    status: done\n  - name: F2\n    status: pending\n")
    r = resolve_source(tmp_path)
    assert r["kind"] == "manifest" and r["stage"] == "prototype"
    assert [f["status"] for f in r["features"]] == ["done", "pending"]


def test_none_when_no_source(tmp_path):
    r = resolve_source(tmp_path)
    assert r["kind"] == "none" and r["features"] == [] and r["stage"] is None


def test_bad_manifest_status_is_error(tmp_path):
    (tmp_path / "project-status.yaml").write_text(
        "project: Z\nfeatures:\n  - name: F\n    status: sorta-done\n")
    r = resolve_source(tmp_path)
    assert r["kind"] == "manifest" and r["error"] and "sorta-done" in r["error"]
