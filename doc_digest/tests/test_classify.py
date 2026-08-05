from doc_digest.config import DigestConfig
from doc_digest.collect import ProjectChanges, DocFile
from doc_digest.classify import build_digest

def _cfg():
    return DigestConfig(base=None, exclude=[], sdd_globs=["docs/superpowers/**"],
                        doc_exts=[".md"], projects=[])

def _pc(name, files, status="ok"):
    return ProjectChanges(name, status, files, None)

def test_two_tier_split():
    files = [DocFile("docs/adr/A.md", "M", 1, "2026-08-06T09:00:00"),
             DocFile("docs/superpowers/plans/p.md", "A", 3, "2026-08-06T10:00:00")]
    d = build_digest(_cfg(), [_pc("P", files)], "s", "u", "g")
    pd = d.projects[0]
    assert [f.path for f in pd.headline] == ["docs/adr/A.md"]
    assert pd.sdd_files == 1 and pd.sdd_commits == 3

def test_ordering_headline_first_then_sdd_then_quiet_then_missing():
    quiet = _pc("Quiet", [])
    sdd = _pc("Sdd", [DocFile("docs/superpowers/x.md", "A", 1, "t")])
    head = _pc("Head", [DocFile("docs/a.md", "M", 1, "t")])
    missing = _pc("Gone", [], status="missing")
    d = build_digest(_cfg(), [quiet, sdd, head, missing], "s", "u", "g")
    assert [p.name for p in d.projects] == ["Head", "Sdd", "Quiet", "Gone"]
    assert d.totals == {"projects": 4, "with_headline": 1, "quiet": 1, "errors": 1}
