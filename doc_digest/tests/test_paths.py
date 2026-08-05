from doc_digest.paths import matches_any

def test_sdd_glob_matches_nested():
    assert matches_any("docs/superpowers/plans/x.md", ["docs/superpowers/**"])

def test_non_sdd_not_matched():
    assert not matches_any("docs/adr/ADR-001.md", ["docs/superpowers/**"])

def test_exclude_nested_node_modules():
    assert matches_any("mobile/node_modules/pkg/readme.md", ["**/node_modules/**"])

def test_empty_globs_never_match():
    assert not matches_any("docs/a.md", [])
