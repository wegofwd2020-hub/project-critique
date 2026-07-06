from portfolio_health.health import assess

EXPL = ["passion", "prototype", "pre-mvp", "spec", "early-build", "unknown"]
FULL_RIGOR = {"has_tests": True, "has_docs": True, "has_license": True}


def _counts(done, inprog, pending):
    t = done + inprog + pending
    return {"total": t, "done": done, "in_progress": inprog, "pending": pending,
            "implemented": done + inprog}


def test_dormant_is_red():
    h = assess(_counts(5, 0, 0), {"last_commit_age_days": 45, "commits_30d": 0},
               FULL_RIGOR, "late-build", "progress", EXPL)
    assert h["status"] == "red" and "dormant" in h["reason"]


def test_low_progress_at_serious_stage_is_red():
    h = assess(_counts(1, 0, 9), {"last_commit_age_days": 3, "commits_30d": 5},
               FULL_RIGOR, "late-build", "progress", EXPL)
    assert h["status"] == "red" and "%" in h["reason"]


def test_no_source_at_serious_stage_is_red():
    h = assess(_counts(0, 0, 0), {"last_commit_age_days": 2, "commits_30d": 1},
               FULL_RIGOR, "shipped", "none", EXPL)
    assert h["status"] == "red" and "no status source" in h["reason"]


def test_slowing_is_yellow():
    h = assess(_counts(8, 1, 1), {"last_commit_age_days": 20, "commits_30d": 2},
               FULL_RIGOR, "late-build", "progress", EXPL)
    assert h["status"] == "yellow" and "slowing" in h["reason"]


def test_partial_progress_is_yellow():
    h = assess(_counts(5, 0, 5), {"last_commit_age_days": 2, "commits_30d": 9},
               FULL_RIGOR, "late-build", "progress", EXPL)
    assert h["status"] == "yellow" and "50%" in h["reason"]


def test_missing_rigor_is_yellow():
    h = assess(_counts(9, 1, 0), {"last_commit_age_days": 2, "commits_30d": 9},
               {"has_tests": False, "has_docs": True, "has_license": True},
               "late-build", "progress", EXPL)
    assert h["status"] == "yellow" and "tests" in h["reason"]


def test_healthy_is_green():
    h = assess(_counts(9, 1, 0), {"last_commit_age_days": 2, "commits_30d": 9},
               FULL_RIGOR, "late-build", "progress", EXPL)
    assert h["status"] == "green"


def test_early_stage_low_progress_not_red():
    # exploratory stage → not marked red for being early
    h = assess(_counts(0, 1, 9), {"last_commit_age_days": 3, "commits_30d": 4},
               FULL_RIGOR, "prototype", "manifest", EXPL)
    assert h["status"] != "red"
