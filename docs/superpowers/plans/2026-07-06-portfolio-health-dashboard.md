# Portfolio Health Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a committed, cron-refreshed portfolio health dashboard in `project-critique` that shows per-repo feature progress, activity, and rigor across all repos — reading each repo's existing progress generator output where available, a manifest otherwise.

**Architecture:** A stdlib-first Python package `project-critique/portfolio_health/`. A collector resolves each repo's feature source by precedence (`docs/progress.json` → `project-status.yaml` → auto-derived), adds git + rigor signals, computes a transparent rule-based health, and writes `portfolio.json`; a renderer turns that into a self-contained `portfolio.html`. Separately, the two existing `generate_progress.py` scripts are extended to emit the normalized `docs/progress.json` they don't yet produce.

**Tech Stack:** Python 3.11+, `PyYAML` (manifest only), stdlib (`subprocess`, `json`, `html`, `pathlib`, `tomllib`), `pytest`.

## Global Constraints

Copied from the spec (`docs/superpowers/specs/2026-07-06-portfolio-health-dashboard-design.md`). Every task implicitly includes these.

- **Python 3.11+.** `requires-python = ">=3.11"`.
- **Deps:** `PyYAML` is the ONLY non-stdlib runtime dep, used solely to parse `project-status.yaml`. Everything else — `progress.json`, git, HTML — is stdlib.
- **The collector is read-only.** It never writes into a scanned repo. It only writes `portfolio.json` + `portfolio.html` into `project-critique`.
- **Feature status is one of exactly three values:** `done`, `in-progress`, `pending`. Every source normalizes to these.
- **Source precedence per repo:** `docs/progress.json` → `project-status.yaml` → none (auto-derived only, flagged `no source`).
- **No bare `except:`.** Specific exception types; any git/fs/parse error on one repo degrades that repo to nulls and never aborts the whole run.
- **Self-contained HTML.** `portfolio.html` has no external resources (no CDN, no remote fonts/scripts); native `<details>` roll-down + an inline JS filter, theme-aware. Mirrors `wegofwd-expenses/expenseweb`.
- **Health is a transparent rule set** with a shown `reason`; thresholds are named constants in `health.py`.

### Normalized shapes (the contracts every task shares)

```
Feature      = {"id": str|None, "name": str, "status": "done"|"in-progress"|"pending", "commits": int|None}
SourceResult = {"kind": "progress"|"manifest"|"none", "stage": str|None,
                "features": list[Feature], "error": str|None}
GitStats     = {"commits_30d": int|None, "last_commit_age_days": int|None, "branch": str|None}
RepoScan     = {"has_tests": bool, "has_docs": bool, "has_license": bool}
Counts       = {"total": int, "done": int, "in_progress": int, "pending": int, "implemented": int}
Health       = {"status": "green"|"yellow"|"red", "reason": str}
ProjectRecord= {"project": str, "stage": str, "source_kind": str, "source_error": str|None,
                "features": list[Feature], "counts": Counts, "git": GitStats,
                "rigor": RepoScan, "health": Health}
Portfolio    = {"generated": str, "root": str, "projects": list[ProjectRecord],
                "summary": {"projects": int, "health": {"green":int,"yellow":int,"red":int},
                            "features": Counts}}
```

---

## File Structure

```
project-critique/
├── portfolio_health/
│   ├── pyproject.toml
│   ├── portfolio_health/
│   │   ├── __init__.py  __main__.py
│   │   ├── sources.py      [Task 1]  progress.json + manifest → SourceResult (precedence)
│   │   ├── gitstats.py     [Task 2]  git → GitStats
│   │   ├── reposcan.py     [Task 3]  fs → RepoScan
│   │   ├── health.py       [Task 4]  counts+git+rigor+stage → Health
│   │   ├── collect.py      [Task 5]  discover repos → Portfolio
│   │   ├── render.py       [Task 6]  Portfolio → portfolio.html
│   │   └── cli.py          [Task 7]  entry point
│   └── tests/
├── config/portfolio.toml   [Task 0]
StudyBuddy_OnDemand/scripts/generate_progress.py   [Task 8]  + docs/progress.json
thittam/scripts/generate_progress.py               [Task 9]  + docs/progress.json
```

Tasks 1–4 are pure functions (fast, isolated). Task 5 composes them. Task 6 renders. Task 7 wires the CLI — the collector is fully usable after Task 7 even before any repo emits `progress.json` (it falls back to manifest/auto-derived). Tasks 8–9 add `progress.json` to the two generators.

---

### Task 0: Scaffold `portfolio_health` package + config

**Files:**
- Create: `portfolio_health/pyproject.toml`, `portfolio_health/portfolio_health/__init__.py`, `__main__.py`, `config/portfolio.toml`

- [ ] **Step 1: pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "portfolio-health"
version = "0.1.0"
description = "Portfolio health dashboard collector + renderer"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.scripts]
portfolio-health = "portfolio_health.cli:main"

[tool.setuptools.packages.find]
include = ["portfolio_health*"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: package files**

`portfolio_health/portfolio_health/__init__.py`: empty.
`portfolio_health/portfolio_health/__main__.py`:
```python
from portfolio_health.cli import main
if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: config/portfolio.toml**

```toml
# Portfolio health dashboard config.
[scan]
root = "~/Documents/code/projects/AIStuff/STEM_studybuddy"
exclude = ["project-critique"]   # don't scan the dashboard's own repo

# Stages that are exploratory — NOT expected to be feature-complete or rigor-heavy,
# so health rules don't mark them red for being early. Everything else "expects" rigor.
exploratory_stages = ["passion", "prototype", "pre-mvp", "spec", "early-build", "unknown"]
```

- [ ] **Step 4: Verify install**

Run: `cd portfolio_health && pip install -e . && python -c "import portfolio_health; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add portfolio_health config/portfolio.toml
git commit -m "chore(portfolio-health): scaffold package + config"
```

---

### Task 1: `sources.py` — feature source resolution

**Files:**
- Create: `portfolio_health/portfolio_health/sources.py`
- Test: `portfolio_health/tests/test_sources.py`

**Interfaces:**
- Produces:
  - `feature_counts(features: list[dict]) -> dict` → Counts.
  - `resolve_source(repo_dir: Path) -> dict` → SourceResult (`kind` progress|manifest|none).

- [ ] **Step 1: Write the failing test**

`portfolio_health/tests/test_sources.py`:
```python
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
```

- [ ] **Step 2: Run → fail** — `cd portfolio_health && python -m pytest tests/test_sources.py -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Write `sources.py`**

```python
"""Resolve a repo's feature list from the first available source:
docs/progress.json (from the repo's own generator) → project-status.yaml
(hand manifest) → none. Every source normalizes to the same Feature shape."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

_VALID = {"done", "in-progress", "pending"}


def feature_counts(features: list[dict]) -> dict:
    """Tally features by status. implemented = done + in-progress."""
    done = sum(1 for f in features if f.get("status") == "done")
    inprog = sum(1 for f in features if f.get("status") == "in-progress")
    pending = sum(1 for f in features if f.get("status") == "pending")
    return {"total": len(features), "done": done, "in_progress": inprog,
            "pending": pending, "implemented": done + inprog}


def _normalize(features: list, error_prefix: str) -> tuple[list[dict], str | None]:
    out, err = [], None
    for f in features or []:
        status = f.get("status")
        if status not in _VALID:
            err = f"{error_prefix}: feature {f.get('name')!r} has bad status {status!r}"
            continue
        out.append({"id": f.get("id"), "name": f.get("name", "(unnamed)"),
                    "status": status, "commits": f.get("commits")})
    return out, err


def resolve_source(repo_dir: Path) -> dict:
    """Return SourceResult for a repo, honoring the precedence."""
    pj = repo_dir / "docs" / "progress.json"
    if pj.is_file():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            feats, err = _normalize(data.get("features"), "progress.json")
            return {"kind": "progress", "stage": data.get("stage"),
                    "features": feats, "error": err}
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            return {"kind": "progress", "stage": None, "features": [],
                    "error": f"unreadable progress.json: {e}"}

    mf = repo_dir / "project-status.yaml"
    if mf.is_file():
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
            feats, err = _normalize(data.get("features"), "project-status.yaml")
            return {"kind": "manifest", "stage": data.get("stage"),
                    "features": feats, "error": err}
        except (OSError, yaml.YAMLError, AttributeError) as e:
            return {"kind": "manifest", "stage": None, "features": [],
                    "error": f"unreadable manifest: {e}"}

    return {"kind": "none", "stage": None, "features": [], "error": None}
```

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_sources.py -v
git add portfolio_health/portfolio_health/sources.py portfolio_health/tests/test_sources.py
git commit -m "feat(portfolio-health): source resolution (progress.json → manifest → none)"
```

---

### Task 2: `gitstats.py` — git activity signals

**Files:**
- Create: `portfolio_health/portfolio_health/gitstats.py`
- Test: `portfolio_health/tests/test_gitstats.py`

**Interfaces:**
- Produces: `git_stats(repo_dir: Path, today: date | None = None) -> dict` → GitStats. `today` is injectable for deterministic age tests.

- [ ] **Step 1: Failing test** (builds a real tmp git repo)

`portfolio_health/tests/test_gitstats.py`:
```python
import subprocess
from datetime import date
from pathlib import Path
from portfolio_health.gitstats import git_stats


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _repo(tmp_path, commit_date="2026-06-01T12:00:00"):
    r = tmp_path / "r"; r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t.com")
    _git(r, "config", "user.name", "t")
    (r / "f.txt").write_text("x")
    _git(r, "add", ".")
    import os
    env = {**os.environ, "GIT_AUTHOR_DATE": commit_date, "GIT_COMMITTER_DATE": commit_date}
    _git(r, "commit", "-qm", "init", env=env)
    return r


def test_stats_on_real_repo(tmp_path):
    r = _repo(tmp_path, "2026-06-20T12:00:00")
    s = git_stats(r, today=date(2026, 7, 6))
    assert s["last_commit_age_days"] == 16
    assert s["commits_30d"] == 1
    assert s["branch"] in ("main", "master")


def test_non_repo_degrades_to_nulls(tmp_path):
    s = git_stats(tmp_path / "not-a-repo", today=date(2026, 7, 6))
    assert s == {"commits_30d": None, "last_commit_age_days": None, "branch": None}
```

- [ ] **Step 2: Run → fail. Step 3: Write `gitstats.py`**

```python
"""Git activity signals for a repo, via the git CLI. Any failure (not a repo,
git missing) degrades to nulls — one bad repo never aborts the portfolio run."""

from __future__ import annotations

import subprocess
from datetime import date, datetime, timezone
from pathlib import Path


def _run(repo_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo_dir), *args],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def git_stats(repo_dir: Path, today: date | None = None) -> dict:
    """Return GitStats. `today` overrides the current date for age math (tests)."""
    null = {"commits_30d": None, "last_commit_age_days": None, "branch": None}
    if _run(repo_dir, "rev-parse", "--is-inside-work-tree") != "true":
        return null
    branch = _run(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    count = _run(repo_dir, "rev-list", "--count", "--since=30.days", "HEAD")
    ts = _run(repo_dir, "log", "-1", "--format=%ct")
    age = None
    if ts and ts.isdigit():
        commit_day = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        age = ((today or datetime.now(timezone.utc).date()) - commit_day).days
    return {"commits_30d": int(count) if count and count.isdigit() else None,
            "last_commit_age_days": age, "branch": branch}
```

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_gitstats.py -v
git add portfolio_health/portfolio_health/gitstats.py portfolio_health/tests/test_gitstats.py
git commit -m "feat(portfolio-health): git activity signals"
```

---

### Task 3: `reposcan.py` — repo rigor signals

**Files:**
- Create: `portfolio_health/portfolio_health/reposcan.py`
- Test: `portfolio_health/tests/test_reposcan.py`

**Interfaces:**
- Produces: `scan_repo(repo_dir: Path) -> dict` → RepoScan.

- [ ] **Step 1: Failing test**

```python
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
```

- [ ] **Step 2: Run → fail. Step 3: Write `reposcan.py`**

```python
"""Repo rigor signals from file presence — mirrors DOCUMENTATION_AUDIT logic."""

from __future__ import annotations

from pathlib import Path


def scan_repo(repo_dir: Path) -> dict:
    """Return RepoScan: has_tests / has_docs / has_license by file presence."""
    has_tests = (repo_dir / "tests").is_dir() or \
        any(repo_dir.rglob("test_*.py")) or any(repo_dir.rglob("*_test.py"))
    has_docs = (repo_dir / "docs").is_dir() or (repo_dir / "README.md").is_file()
    has_license = any(repo_dir.glob("LICENSE*"))
    return {"has_tests": bool(has_tests), "has_docs": bool(has_docs),
            "has_license": bool(has_license)}
```

Note: `rglob` can be slow on huge trees; acceptable for this nightly tool. If a repo is enormous, a later optimization can cap depth — out of scope for v1.

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_reposcan.py -v
git add portfolio_health/portfolio_health/reposcan.py portfolio_health/tests/test_reposcan.py
git commit -m "feat(portfolio-health): repo rigor signals"
```

---

### Task 4: `health.py` — transparent rule-based status

**Files:**
- Create: `portfolio_health/portfolio_health/health.py`
- Test: `portfolio_health/tests/test_health.py`

**Interfaces:**
- Consumes: Counts, GitStats, RepoScan, stage, source_kind.
- Produces: `assess(counts, git, rigor, stage, source_kind, exploratory_stages) -> dict` → Health.

- [ ] **Step 1: Failing test (one per rule branch)**

```python
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
```

- [ ] **Step 2: Run → fail. Step 3: Write `health.py`**

```python
"""Transparent, ordered health rules → (status, reason). Thresholds are named
constants so they are easy to tune after the first real run."""

from __future__ import annotations

DORMANT_DAYS = 30
SLOWING_DAYS = 14
LOW_PROGRESS = 0.25    # below this at a serious stage → red
OK_PROGRESS = 0.70     # below this → yellow


def _progress(counts: dict) -> float | None:
    return counts["done"] / counts["total"] if counts["total"] else None


def assess(counts: dict, git: dict, rigor: dict, stage: str | None,
           source_kind: str, exploratory_stages: list[str]) -> dict:
    """Return Health. Rules are ordered; the first that fires wins."""
    stage = stage or "unknown"
    expects = stage not in exploratory_stages
    age = git.get("last_commit_age_days")
    prog = _progress(counts)
    pct = None if prog is None else round(prog * 100)

    if age is not None and age > DORMANT_DAYS:
        return {"status": "red", "reason": f"dormant — no commits in {age}d"}
    if prog is not None and prog < LOW_PROGRESS and expects:
        return {"status": "red", "reason": f"only {pct}% of features done at {stage} stage"}
    if source_kind == "none" and expects:
        return {"status": "red", "reason": "no status source (add progress.json or project-status.yaml)"}
    if age is not None and SLOWING_DAYS < age <= DORMANT_DAYS:
        return {"status": "yellow", "reason": f"slowing — {age}d since last commit"}
    if prog is not None and prog < OK_PROGRESS:
        return {"status": "yellow", "reason": f"{pct}% of features done"}
    missing = [k for k in ("tests", "docs") if not rigor.get(f"has_{k}")]
    if missing:
        return {"status": "yellow", "reason": f"missing {', '.join(missing)}"}
    tail = f"{pct}% done" if pct is not None else "no feature list"
    return {"status": "green", "reason": f"active, {tail}, tests+docs"}
```

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_health.py -v
git add portfolio_health/portfolio_health/health.py portfolio_health/tests/test_health.py
git commit -m "feat(portfolio-health): transparent rule-based health"
```

---

### Task 5: `collect.py` — discover repos → Portfolio

**Files:**
- Create: `portfolio_health/portfolio_health/collect.py`
- Test: `portfolio_health/tests/test_collect.py`

**Interfaces:**
- Consumes: `resolve_source`, `git_stats`, `scan_repo`, `assess`, `feature_counts`.
- Produces: `collect(root: Path, exclude: list[str], exploratory_stages: list[str], today=None) -> dict` → Portfolio.

- [ ] **Step 1: Failing test**

```python
import json, subprocess, os
from datetime import date
from pathlib import Path
from portfolio_health.collect import collect


def _make_repo(root, name, progress=None):
    r = root / name; (r / "docs").mkdir(parents=True)
    subprocess.run(["git", "-C", str(r), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.email", "t@t.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "config", "user.name", "t"], check=True, capture_output=True)
    if progress is not None:
        (r / "docs" / "progress.json").write_text(json.dumps(progress))
    (r / "f").write_text("x")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    env = {**os.environ, "GIT_AUTHOR_DATE": "2026-07-01T12:00:00",
           "GIT_COMMITTER_DATE": "2026-07-01T12:00:00"}
    subprocess.run(["git", "-C", str(r), "commit", "-qm", "i"], check=True, capture_output=True, env=env)
    return r


def test_collect_two_repos(tmp_path):
    _make_repo(tmp_path, "alpha", progress={
        "project": "Alpha", "stage": "late-build",
        "features": [{"name": "A", "status": "done"}, {"name": "B", "status": "pending"}]})
    _make_repo(tmp_path, "skipme")
    port = collect(tmp_path, exclude=["skipme"], exploratory_stages=["unknown"],
                   today=date(2026, 7, 6))
    assert port["summary"]["projects"] == 1
    p = port["projects"][0]
    assert p["project"] == "Alpha" and p["counts"]["done"] == 1
    assert p["source_kind"] == "progress" and p["health"]["status"] in {"green", "yellow", "red"}
    assert port["summary"]["features"]["total"] == 2


def test_repo_without_source_flagged(tmp_path):
    _make_repo(tmp_path, "beta")  # no progress.json, no manifest
    port = collect(tmp_path, exclude=[], exploratory_stages=["unknown"], today=date(2026, 7, 6))
    assert port["projects"][0]["source_kind"] == "none"
```

- [ ] **Step 2: Run → fail. Step 3: Write `collect.py`**

```python
"""Discover git repos under the root and assemble the Portfolio record."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from portfolio_health.gitstats import git_stats
from portfolio_health.health import assess
from portfolio_health.reposcan import scan_repo
from portfolio_health.sources import feature_counts, resolve_source


def _iter_repos(root: Path, exclude: list[str]):
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if child.name in exclude or not (child / ".git").exists():
            continue
        yield child


def collect(root: Path, exclude: list[str], exploratory_stages: list[str],
            today: date | None = None) -> dict:
    """Scan every git repo under `root` (minus `exclude`) into a Portfolio."""
    root = Path(root).expanduser()
    today = today or datetime.now(timezone.utc).date()
    projects, health_tally = [], {"green": 0, "yellow": 0, "red": 0}
    totals = {"total": 0, "done": 0, "in_progress": 0, "pending": 0, "implemented": 0}

    for repo in _iter_repos(root, exclude):
        src = resolve_source(repo)
        counts = feature_counts(src["features"])
        git = git_stats(repo, today=today)
        rigor = scan_repo(repo)
        stage = src["stage"] or "unknown"
        health = assess(counts, git, rigor, stage, src["kind"], exploratory_stages)
        health_tally[health["status"]] += 1
        for k in totals:
            totals[k] += counts[k]
        projects.append({
            "project": repo.name, "stage": stage, "source_kind": src["kind"],
            "source_error": src["error"], "features": src["features"],
            "counts": counts, "git": git, "rigor": rigor, "health": health,
        })

    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "root": str(root),
            "projects": projects,
            "summary": {"projects": len(projects), "health": health_tally,
                        "features": totals}}
```

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_collect.py -v
git add portfolio_health/portfolio_health/collect.py portfolio_health/tests/test_collect.py
git commit -m "feat(portfolio-health): repo discovery + portfolio assembly"
```

---

### Task 6: `render.py` — self-contained HTML dashboard

**Files:**
- Create: `portfolio_health/portfolio_health/render.py`
- Test: `portfolio_health/tests/test_render.py`

**Interfaces:**
- Consumes: Portfolio (Task 5).
- Produces: `build_html(portfolio: dict) -> str`.

- [ ] **Step 1: Failing test**

```python
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
```

- [ ] **Step 2: Run → fail. Step 3: Write `render.py`**

```python
"""Render a Portfolio to a single self-contained HTML dashboard: one roll-down
row per project (health dot, stage, feature counts, activity), a top summary,
and an inline filter box. No external resources. Mirrors expenseweb."""

from __future__ import annotations

from html import escape

_DOT = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

_STYLE = """
:root{color-scheme:light dark;--fg:#1a1a1a;--bg:#fff;--mut:#666;--line:#e2e2e2;
--card:#f7f7f8;--accent:#2563eb;}
@media(prefers-color-scheme:dark){:root{--fg:#e8e8e8;--bg:#151517;--mut:#9a9a9a;
--line:#2c2c30;--card:#1e1e22;--accent:#6ea8fe;}}
*{box-sizing:border-box}body{margin:0;padding:2rem 1rem;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto}h1{font-size:1.5rem;margin:0 0 .25rem}
.sub{color:var(--mut);margin:0 0 1.25rem}
.grand{display:flex;gap:.6rem;flex-wrap:wrap;margin:0 0 1rem}
.grand .g{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.5rem .8rem}
#q{width:100%;padding:.6rem .8rem;margin:0 0 1.25rem;font:inherit;color:var(--fg);
background:var(--card);border:1px solid var(--line);border-radius:10px}
#q:focus{outline:2px solid var(--accent);outline-offset:1px}
#none{display:none;color:var(--mut);padding:2rem 0;text-align:center}
details{border:1px solid var(--line);border-radius:10px;margin:.5rem 0;background:var(--card)}
summary{cursor:pointer;list-style:none;padding:.7rem 1rem;display:flex;gap:1rem;
align-items:center;flex-wrap:wrap}
summary::-webkit-details-marker{display:none}
.name{font-weight:600;min-width:12rem}.stage{color:var(--mut);font-size:.85rem}
.counts{margin-left:auto;font-variant-numeric:tabular-nums;font-size:.9rem}
.reason{color:var(--mut);font-size:.85rem;flex-basis:100%}
.body{padding:.25rem 1rem 1rem}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{text-align:left;padding:.35rem .5rem;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:500;font-size:.8rem;text-transform:uppercase}
.sig{color:var(--mut);font-size:.85rem;margin-top:.5rem}
.badge{font-size:.75rem;border:1px solid var(--mut);border-radius:5px;padding:0 .35rem;margin-left:.4rem;color:var(--mut)}
""".strip()

_SCRIPT = """
(function(){var q=document.getElementById('q');if(!q)return;
var rows=[].slice.call(document.querySelectorAll('details.proj'));var none=document.getElementById('none');
function apply(){var s=q.value.trim().toLowerCase();var any=false;
rows.forEach(function(d){var hit=!s||d.textContent.toLowerCase().indexOf(s)!==-1;
d.style.display=hit?'':'none';if(hit)any=true;});
if(none)none.style.display=(s&&!any)?'':'none';}
q.addEventListener('input',apply);})();
""".strip()


def _counts_str(c: dict) -> str:
    return f'{c["done"]}✓ / {c["in_progress"]}⏳ / {c["pending"]}◻'


def build_html(portfolio: dict) -> str:
    p = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         "<title>Portfolio Health</title>", f"<style>{_STYLE}</style></head><body>",
         '<div class="wrap"><h1>Portfolio Health</h1>']
    s = portfolio["summary"]
    p.append(f'<p class="sub">{s["projects"]} repos · generated '
             f'{escape(portfolio["generated"])}</p>')
    h = s["health"]; f = s["features"]
    p.append('<div class="grand">'
             f'<div class="g">🟢 {h["green"]} · 🟡 {h["yellow"]} · 🔴 {h["red"]}</div>'
             f'<div class="g">features: {f["done"]}✓ / {f["in_progress"]}⏳ / {f["pending"]}◻ '
             f'(of {f["total"]})</div></div>')

    if not portfolio["projects"]:
        p.append('<p class="sub">No repositories found.</p></div></body></html>')
        return "\n".join(p)

    p.append('<input id="q" type="search" autocomplete="off" '
             'placeholder="Filter by project, stage, status, owner…">')
    p.append('<div id="none">No matching repositories.</div>')

    for pr in portfolio["projects"]:
        src_badge = "" if pr["source_kind"] != "none" else '<span class="badge">no source</span>'
        err_badge = f'<span class="badge">source error</span>' if pr["source_error"] else ""
        p.append('<details class="proj"><summary>'
                 f'<span>{_DOT.get(pr["health"]["status"], "")}</span>'
                 f'<span class="name">{escape(pr["project"])}{src_badge}{err_badge}</span>'
                 f'<span class="stage">{escape(pr["stage"])}</span>'
                 f'<span class="counts">{_counts_str(pr["counts"])} · '
                 f'{pr["git"]["commits_30d"] if pr["git"]["commits_30d"] is not None else "–"}c/30d · '
                 f'{pr["git"]["last_commit_age_days"] if pr["git"]["last_commit_age_days"] is not None else "–"}d</span>'
                 f'<span class="reason">{escape(pr["health"]["reason"])}</span></summary>')
        p.append('<div class="body">')
        if pr["features"]:
            p.append("<table><tr><th>Feature</th><th>Status</th><th>ID</th></tr>")
            for ft in pr["features"]:
                p.append(f'<tr><td>{escape(ft["name"])}</td>'
                         f'<td>{escape(ft["status"])}</td>'
                         f'<td>{escape(str(ft.get("id") or ""))}</td></tr>')
            p.append("</table>")
        r = pr["rigor"]
        p.append(f'<div class="sig">tests: {"yes" if r["has_tests"] else "no"} · '
                 f'docs: {"yes" if r["has_docs"] else "no"} · '
                 f'license: {"yes" if r["has_license"] else "no"} · '
                 f'branch: {escape(str(pr["git"]["branch"] or "–"))}</div>')
        if pr["source_error"]:
            p.append(f'<div class="sig">source error: {escape(pr["source_error"])}</div>')
        p.append("</div></details>")

    p.append(f"<script>{_SCRIPT}</script></div></body></html>")
    return "\n".join(p)
```

- [ ] **Step 4: Run → pass. Commit**

```bash
cd portfolio_health && python -m pytest tests/test_render.py -v
git add portfolio_health/portfolio_health/render.py portfolio_health/tests/test_render.py
git commit -m "feat(portfolio-health): self-contained HTML dashboard with filter + roll-down"
```

---

### Task 7: `cli.py` — entry point + wiring

**Files:**
- Create: `portfolio_health/portfolio_health/cli.py`
- Test: `portfolio_health/tests/test_cli.py`

**Interfaces:**
- Produces: `main(argv=None) -> int` — `portfolio-health --config <toml> --json <path> --html <path>` (or `--root` to override).

- [ ] **Step 1: Failing test**

```python
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
```

- [ ] **Step 2: Run → fail. Step 3: Write `cli.py`**

```python
"""CLI: read config, collect the portfolio, write portfolio.json + portfolio.html."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from portfolio_health.collect import collect
from portfolio_health.render import build_html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="portfolio-health")
    ap.add_argument("--config", required=True)
    ap.add_argument("--json", required=True, dest="json_out")
    ap.add_argument("--html", required=True, dest="html_out")
    ap.add_argument("--root", default=None, help="override config scan.root")
    args = ap.parse_args(argv)
    try:
        with open(args.config, "rb") as fh:
            cfg = tomllib.load(fh).get("scan", {})
        root = args.root or cfg.get("root", ".")
        portfolio = collect(Path(root).expanduser(),
                            exclude=cfg.get("exclude", []),
                            exploratory_stages=cfg.get("exploratory_stages", ["unknown"]))
        Path(args.json_out).write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
        Path(args.html_out).write_text(build_html(portfolio), encoding="utf-8")
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"portfolio-health: {e}", file=sys.stderr)
        return 1
    s = portfolio["summary"]
    print(f"portfolio-health: {s['projects']} repos "
          f"(🟢{s['health']['green']} 🟡{s['health']['yellow']} 🔴{s['health']['red']}) "
          f"→ {args.html_out}")
    return 0
```

- [ ] **Step 4: Run → pass. Full suite green. Commit**

```bash
cd portfolio_health && python -m pytest -q
git add portfolio_health/portfolio_health/cli.py portfolio_health/tests/test_cli.py
git commit -m "feat(portfolio-health): CLI wiring (config → portfolio.json + portfolio.html)"
```

**CHECKPOINT:** the collector is now fully usable. Running it against the real portfolio produces a dashboard from manifests + auto-derived signals even before Tasks 8–9 add `progress.json`.

---

### Task 8: Emit `docs/progress.json` from StudyBuddy's generator

**Files:**
- Modify: `StudyBuddy_OnDemand/scripts/generate_progress.py`
- Test: `StudyBuddy_OnDemand/tests/test_progress_json.py` (or the repo's existing test dir)

**Interfaces:**
- Produces: `StudyBuddy_OnDemand/docs/progress.json` — normalized `{project, generated, source:"epics", stage?, features:[{id,name,status,commits}]}`.

**Context:** `generate_progress.py` already has `parse_epics()` → `{num: {num,title,status,file,...}}` and `attribute_commits(commits, epics)` which sets `c["epics"]`. The epic `status` is free text containing an emoji (`✅`/`🚧`/`🔜`/`💭`) or blank.

- [ ] **Step 1: Write the failing test**

`StudyBuddy_OnDemand/tests/test_progress_json.py`:
```python
from scripts.generate_progress import build_progress_json, _status_to_canonical


def test_status_mapping():
    assert _status_to_canonical("✅ Complete") == "done"
    assert _status_to_canonical("🚧 In Progress (K-1)") == "in-progress"
    assert _status_to_canonical("🔜 Ready to build") == "pending"
    assert _status_to_canonical("💭 Your call") == "pending"
    assert _status_to_canonical("") == "pending"


def test_build_progress_json_shape():
    epics = {1: {"num": 1, "title": "Epic 1 — Foo", "status": "✅ Complete", "file": "EPIC_01_foo.md"},
             4: {"num": 4, "title": "Epic 4 — Bar", "status": "💭 Your call", "file": "EPIC_04_bar.md"}}
    commits = [{"epics": [1]}, {"epics": [1]}, {"epics": []}]
    doc = build_progress_json(epics, commits)
    assert doc["source"] == "epics" and doc["project"] == "StudyBuddy OnDemand"
    feats = {f["id"]: f for f in doc["features"]}
    assert feats["Epic 1"]["status"] == "done" and feats["Epic 1"]["commits"] == 2
    assert feats["Epic 1"]["name"] == "Foo"      # "Epic N —" prefix stripped
    assert feats["Epic 4"]["status"] == "pending" and feats["Epic 4"]["commits"] == 0
```

- [ ] **Step 2: Run → fail.** `cd StudyBuddy_OnDemand && python -m pytest tests/test_progress_json.py -v` → ImportError.

- [ ] **Step 3: Add the functions + JSON write to `generate_progress.py`**

Add near the top (after imports):
```python
import json as _json

OUTPUT_JSON = REPO / "docs" / "progress.json"


def _status_to_canonical(status: str) -> str:
    """Map an epic's free-text status to done | in-progress | pending."""
    if "✅" in status:
        return "done"
    if "🚧" in status:
        return "in-progress"
    return "pending"      # 🔜 / 💭 / blank / anything else


def build_progress_json(epics: dict[int, dict], commits: list[dict]) -> dict:
    """Normalized machine-readable feature list for the portfolio dashboard."""
    commit_counts: dict[int, int] = {}
    for c in commits:
        for n in c.get("epics", []):
            commit_counts[n] = commit_counts.get(n, 0) + 1
    features = []
    for num in sorted(epics):
        e = epics[num]
        name = re.sub(r"^Epic \d+\s*[—-]\s*", "", e["title"]).strip()
        features.append({"id": f"Epic {num}", "name": name,
                         "status": _status_to_canonical(e["status"]),
                         "commits": commit_counts.get(num, 0)})
    return {"project": "StudyBuddy OnDemand",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "epics", "stage": "late-build", "features": features}
```

In `main()`, after `attribute_commits(commits, epics)` and the existing
`OUTPUT.write_text(document)`, add:
```python
    OUTPUT_JSON.write_text(_json.dumps(build_progress_json(epics, commits), indent=2))
```

- [ ] **Step 4: Run → pass** (`tests/test_progress_json.py`). Sanity-run the generator if the repo has `docs/epics/`: `python scripts/generate_progress.py` and confirm `docs/progress.json` appears with the right shape.

- [ ] **Step 5: Commit (in StudyBuddy_OnDemand)**

```bash
cd StudyBuddy_OnDemand
git add scripts/generate_progress.py tests/test_progress_json.py
git commit -m "feat(progress): emit normalized docs/progress.json for the portfolio dashboard"
```

---

### Task 9: Emit `docs/progress.json` from thittam's generator

**Files:**
- Modify: `thittam/scripts/generate_progress.py`
- Test: `thittam/tests/test_progress_json.py`

**Interfaces:**
- Produces: `thittam/docs/progress.json` — same schema, `source:"issues"`.

**Context:** thittam's generator models features as GitHub issues/PRs. `fetch_issues()` → `{number: {number,title,state,...}}` (state is `OPEN`/`CLOSED`; PRs may be `MERGED`). `get_commits()` gives each commit `c["issues"] = [int,...]`. Map: an issue is **done** if closed/merged; **in-progress** if open with ≥1 attributed commit; **pending** if open with 0 commits.

- [ ] **Step 1: Failing test**

`thittam/tests/test_progress_json.py`:
```python
from scripts.generate_progress import build_progress_json, _issue_status


def test_issue_status():
    assert _issue_status("CLOSED", commits=0) == "done"
    assert _issue_status("MERGED", commits=0) == "done"
    assert _issue_status("OPEN", commits=3) == "in-progress"
    assert _issue_status("OPEN", commits=0) == "pending"


def test_build_progress_json_shape():
    issues = {12: {"number": 12, "title": "Billing", "state": "CLOSED"},
              18: {"number": 18, "title": "Auth", "state": "OPEN"}}
    commits = [{"issues": [18]}, {"issues": [18]}, {"issues": []}]
    doc = build_progress_json(issues, commits)
    assert doc["source"] == "issues" and doc["project"] == "Thittam"
    feats = {f["id"]: f for f in doc["features"]}
    assert feats["#12"]["status"] == "done" and feats["#12"]["name"] == "Billing"
    assert feats["#18"]["status"] == "in-progress" and feats["#18"]["commits"] == 2
```

- [ ] **Step 2: Run → fail. Step 3: Add functions + JSON write**

Near the top of `thittam/scripts/generate_progress.py`:
```python
OUTPUT_JSON = REPO / "docs" / "progress.json"


def _issue_status(state: str, commits: int) -> str:
    """Map a GitHub issue/PR state (+ commit activity) to the canonical set."""
    if state in ("CLOSED", "MERGED"):
        return "done"
    return "in-progress" if commits > 0 else "pending"


def build_progress_json(issues: dict[int, dict], commits: list[dict]) -> dict:
    """Normalized feature list from issues/PRs referenced in commits + their state."""
    commit_counts: dict[int, int] = {}
    for c in commits:
        for n in c.get("issues", []):
            commit_counts[n] = commit_counts.get(n, 0) + 1
    numbers = set(commit_counts) | set(issues)
    features = []
    for n in sorted(numbers):
        meta = issues.get(n, {})
        cnt = commit_counts.get(n, 0)
        features.append({"id": f"#{n}", "name": meta.get("title", f"issue {n}"),
                         "status": _issue_status(meta.get("state", "OPEN"), cnt),
                         "commits": cnt})
    return {"project": "Thittam",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "issues", "stage": "late-build", "features": features}
```

In `main()`, after `document = render(...)` and `OUTPUT.write_text(document)`:
```python
    import json as _json
    OUTPUT_JSON.write_text(_json.dumps(build_progress_json(issues, commits), indent=2))
```

- [ ] **Step 4: Run → pass. Step 5: Commit (in thittam)**

```bash
cd thittam
git add scripts/generate_progress.py tests/test_progress_json.py
git commit -m "feat(progress): emit normalized docs/progress.json for the portfolio dashboard"
```

---

### Task 10: Cron wrapper + first real run + seed manifests

**Files:**
- Create: `project-critique/portfolio_health/scripts/refresh.sh`
- Create: `project-status.yaml` in a few repos that have no generator (manual, per owners)

- [ ] **Step 1: Write `refresh.sh`**

```bash
#!/usr/bin/env bash
# Refresh the portfolio dashboard: pull repos, collect, commit the snapshot.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # project-critique
PORTFOLIO_ROOT="${PORTFOLIO_ROOT:-$HOME/Documents/code/projects/AIStuff/STEM_studybuddy}"
PY="${PYTHON:-$ROOT/portfolio_health/.venv/bin/python}"
[ -x "$PY" ] || PY=python3
"$PY" -m portfolio_health \
    --config "$ROOT/config/portfolio.toml" \
    --json "$ROOT/portfolio.json" \
    --html "$ROOT/portfolio.html" || exit 1
cd "$ROOT"
if ! git diff --quiet portfolio.json portfolio.html; then
  git add portfolio.json portfolio.html
  git commit -m "chore(portfolio): refresh health snapshot $(date -u +%Y-%m-%d)"
  git push
fi
```

- [ ] **Step 2: First real run** — from `project-critique`:
  `python -m portfolio_health --config config/portfolio.toml --json portfolio.json --html portfolio.html`
  Open `portfolio.html`, sanity-check: StudyBuddy/thittam show `source: progress` once Tasks 8–9 have run in those repos; others show `no source` until seeded.

- [ ] **Step 3: Seed manifests** — for the active non-generator repos (Mentible, pramana, kathai-chithiram, MarketingTools, dronePrjs, mambakkam-net), add a `project-status.yaml` bootstrapped from `PORTFOLIO_SCORECARD.md`/`PRODUCT_CATALOG.md` stage + a first feature list; owners refine. Do NOT add manifests to StudyBuddy_OnDemand or thittam (they emit `progress.json`).

- [ ] **Step 4: Install cron** (lead's machine):
  `( crontab -l 2>/dev/null; echo "30 7 * * * $PWD/portfolio_health/scripts/refresh.sh" ) | crontab -`

- [ ] **Step 5: Commit** the wrapper + first snapshot + any seeded manifests' presence note.

```bash
git add portfolio_health/scripts/refresh.sh portfolio.json portfolio.html
git commit -m "ops(portfolio): daily refresh wrapper + first health snapshot"
```

---

## Self-Review

**Spec coverage:**
- §2 architecture (sources/gitstats/reposcan/health/collect/render/cli) → Tasks 1–7. ✓
- §3 source precedence + progress.json + manifest → Task 1 (`resolve_source`), Tasks 8–9 (emit progress.json). ✓
- §3a status mapping (✅/🚧/🔜/💭 → canonical) → Task 8 `_status_to_canonical`, Task 9 `_issue_status`. ✓
- §4 git + rigor signals → Tasks 2, 3. ✓
- §5 health rules (each branch) → Task 4 with a test per branch. ✓
- §6 dashboard (summary, filter, per-project roll-down, no-source badge, self-contained) → Task 6. ✓
- §7 orchestration (cli, cron, committed snapshot) → Tasks 7, 10. ✓
- §8 testing (no network; tmp git repos; normalization; each rule) → tests throughout; generator tests in Tasks 8–9. ✓
- §9 phasing (collector + generator extension + seed manifests, not both sources on one repo) → Task 10 Step 3 explicitly excludes StudyBuddy/thittam from manifests. ✓

**Placeholder scan:** No TBD/"add error handling"/vague steps; every code step has full code. Task 10 Step 3 (seed manifests) is inherently human/owner content (feature lists per repo) — the mechanism and an example are specified; the per-repo feature text is the owners' to supply, not a code placeholder.

**Type consistency:** `resolve_source`→SourceResult keys (`kind/stage/features/error`) consumed identically in `collect`. `feature_counts`→Counts keys (`total/done/in_progress/pending/implemented`) used in `collect`, `health.assess`, `render`. `git_stats`→GitStats (`commits_30d/last_commit_age_days/branch`) used in `assess`+`render`. `assess(counts, git, rigor, stage, source_kind, exploratory_stages)` call site in `collect` matches. `build_html(portfolio)` consumes the exact Portfolio shape `collect` produces. Generator `build_progress_json` output matches the `progress.json` schema `resolve_source` reads (`features:[{id,name,status,commits}]`, `stage`). Consistent.

**One verification for the executor:** confirm each target repo's test layout — Tasks 8–9 assume `import from scripts.generate_progress`; if a repo's pytest config doesn't put the repo root on the path, add a `conftest.py` (sys.path shim) or run tests with `PYTHONPATH=.`. Mechanical, repo-local.
