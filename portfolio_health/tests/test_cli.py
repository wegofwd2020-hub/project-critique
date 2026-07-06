import json, subprocess, os
from pathlib import Path
from portfolio_health.cli import main


def _repo(root, name):
    r = root / name; (r / "docs").mkdir(parents=True)
    for a in (["init", "-q"], ["config", "user.email", "t@t.com"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)
    (r / "docs" / "progress.json").write_text(json.dumps(
        {"project": name, "stage": "late-build",
         "features": [{"name": "A", "status": "done"}]}))
    (r / "f").write_text("x")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "i"], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_DATE": "2026-07-01T12:00:00",
                        "GIT_COMMITTER_DATE": "2026-07-01T12:00:00"})


def test_cli_writes_json_and_html(tmp_path):
    _repo(tmp_path, "alpha")
    cfg = tmp_path / "portfolio.toml"
    cfg.write_text(f'[scan]\nroot = "{tmp_path}"\nexclude = []\n'
                   'exploratory_stages = ["unknown"]\n')
    outj = tmp_path / "portfolio.json"; outh = tmp_path / "portfolio.html"
    rc = main(["--config", str(cfg), "--json", str(outj), "--html", str(outh)])
    assert rc == 0
    data = json.loads(outj.read_text())
    assert data["summary"]["projects"] == 1
    assert outh.read_text().strip().startswith("<!doctype html>")
