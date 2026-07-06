from portfolio_health.reposcan import scan_repo


def test_full_repo(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "LICENSE").write_text("MIT")
    assert scan_repo(tmp_path) == {"has_tests": True, "has_docs": True, "has_license": True}


def test_readme_counts_as_docs_and_test_file(tmp_path):
    (tmp_path / "README.md").write_text("# x")
    (tmp_path / "test_thing.py").write_text("def test_x(): pass")
    s = scan_repo(tmp_path)
    assert s["has_docs"] is True and s["has_tests"] is True and s["has_license"] is False


def test_bare_repo(tmp_path):
    assert scan_repo(tmp_path) == {"has_tests": False, "has_docs": False, "has_license": False}
