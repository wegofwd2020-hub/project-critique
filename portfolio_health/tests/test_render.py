from portfolio_health.render import build_html

PORT = {"generated": "2026-07-06T00:00:00+00:00", "root": "/x",
        "projects": [
            {"project": "Alpha", "stage": "late-build", "source_kind": "progress",
             "source_error": None,
             "features": [{"id": "Epic 1", "name": "A & B", "status": "done", "commits": 3},
                          {"id": None, "name": "C", "status": "pending", "commits": 0}],
             "counts": {"total": 2, "done": 1, "in_progress": 0, "pending": 1, "implemented": 1},
             "git": {"commits_30d": 4, "last_commit_age_days": 2, "branch": "main"},
             "rigor": {"has_tests": True, "has_docs": True, "has_license": False},
             "health": {"status": "yellow", "reason": "50% of features done"}}],
        "summary": {"projects": 1, "health": {"green": 0, "yellow": 1, "red": 0},
                    "features": {"total": 2, "done": 1, "in_progress": 0, "pending": 1, "implemented": 1}}}


def test_self_contained(tmp_path):
    html = build_html(PORT)
    assert html.strip().startswith("<!doctype html>")
    assert "http://" not in html and "https://" not in html and "src=" not in html


def test_shows_project_and_counts_and_health(tmp_path):
    html = build_html(PORT)
    assert "Alpha" in html and "late-build" in html
    assert "yellow" in html and "50% of features done" in html
    assert "<details" in html                       # roll-down per project
    assert 'id="q"' in html and "addEventListener('input'" in html  # filter


def test_escapes_and_lists_features(tmp_path):
    html = build_html(PORT)
    assert "A &amp; B" in html and "<b>" not in html   # escaped feature name
    assert "Epic 1" in html


def test_empty_portfolio_message():
    html = build_html({"generated": "t", "root": "/x", "projects": [],
                       "summary": {"projects": 0, "health": {"green": 0, "yellow": 0, "red": 0},
                                   "features": {"total": 0, "done": 0, "in_progress": 0,
                                                "pending": 0, "implemented": 0}}})
    assert "no repositories" in html.lower()
