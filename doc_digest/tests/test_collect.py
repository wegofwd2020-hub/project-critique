from doc_digest.config import DigestConfig, ProjectCfg
from doc_digest.collect import collect_project

def _cfg(base):
    return DigestConfig(base=base, exclude=["**/node_modules/**"],
                        sdd_globs=["docs/superpowers/**"], doc_exts=[".md"],
                        projects=[])

def test_dedup_and_filter(gitrepo):
    gitrepo.commit({"docs/a.md": "1", "docs/x.py": "code", "docs/node_modules/n.md": "n"}, "2026-08-06T09:00:00")
    gitrepo.commit({"docs/a.md": "2"}, "2026-08-06T12:00:00")
    base = gitrepo.path.parent
    (base / "Proj").symlink_to(gitrepo.path)   # project name -> repo dir
    ch = collect_project(_cfg(base), ProjectCfg("Proj", ["docs"]),
                         "2026-08-05T00:00:00", "2026-08-07T00:00:00")
    assert ch.status == "ok"
    paths = sorted(f.path for f in ch.files)
    assert paths == ["docs/a.md"]              # .py dropped, node_modules excluded
    a = ch.files[0]
    assert a.commits == 2 and a.last_date.startswith("2026-08-06T12")

def test_missing_repo(tmp_path):
    ch = collect_project(_cfg(tmp_path), ProjectCfg("Nope", ["docs"]),
                         "2026-08-05T00:00:00", "2026-08-07T00:00:00")
    assert ch.status == "missing" and ch.files == []
