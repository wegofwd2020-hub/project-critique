from doc_digest.collect import ProjectChanges, DocFile
from doc_digest.classify import build_digest
from doc_digest.config import DigestConfig
from doc_digest.render import render_markdown, render_html

def _digest():
    cfg = DigestConfig(base=None, exclude=[], sdd_globs=["docs/superpowers/**"], doc_exts=[".md"], projects=[])
    head = ProjectChanges("Head", "ok", [DocFile("docs/a.md", "M", 2, "2026-08-06T09:00:00")], None)
    sdd = ProjectChanges("Sdd", "ok", [DocFile("docs/superpowers/x.md", "A", 4, "2026-08-06T09:00:00")], None)
    miss = ProjectChanges("Gone", "missing", [], None)
    return build_digest(cfg, [head, sdd, miss], "2026-08-03", "2026-08-10", "2026-08-10T07:45")

def test_markdown_has_table_and_details():
    md = render_markdown(_digest())
    assert "# Weekly Doc Digest — 2026-08-10" in md
    assert "window: 2026-08-03 → 2026-08-10" in md
    assert "docs/a.md" in md and "modified" in md
    assert "1 files / 4 commits" in md   # SDD collapsed count for Sdd project (1 file, 4 commits)
    assert "MISSING" in md               # Gone project flagged

def test_html_is_self_contained():
    html = render_html(_digest())
    assert html.lstrip().startswith("<!doctype html>")
    assert "<style" in html and "http" not in html.split("<style")[0]  # no external refs before styles
    assert "Head" in html and "Gone" in html
