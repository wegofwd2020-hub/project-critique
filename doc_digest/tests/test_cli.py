import textwrap
from pathlib import Path
from doc_digest.cli import main

def test_end_to_end(tmp_path, gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-08-06T09:00:00")
    base = gitrepo.path.parent
    (base / "Proj").symlink_to(gitrepo.path)
    cfg = tmp_path / "d.toml"
    cfg.write_text(textwrap.dedent(f"""
        base = "{base}"
        sdd_globs = ["docs/superpowers/**"]
        [[project]]
        name = "Proj"
        include = ["docs"]
    """))
    md, html = tmp_path / "out.md", tmp_path / "out.html"
    rc = main(["--config", str(cfg), "--as-of", "2026-08-10T00:00:00",
               "--since-days", "7", "--out-md", str(md), "--out-html", str(html)])
    assert rc == 0
    assert "docs/a.md" in md.read_text()
    assert html.read_text().lstrip().startswith("<!doctype html>")
