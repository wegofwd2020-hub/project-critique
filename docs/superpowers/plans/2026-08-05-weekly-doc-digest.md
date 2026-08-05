# Weekly Doc Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone, read-only tool in `project-critique` that emits a weekly committed report of what documentation changed across 10 portfolio projects.

**Architecture:** A small stdlib-only Python package (`doc_digest/`) that reads each repo's git history over a 7-day window, filters to documents via a per-project path map, splits changes into a headline tier (listed) and an SDD tier (`superpowers/**`, collapsed to a count), and renders markdown + self-contained HTML. A shell wrapper runs it weekly via cron and commits the output with rebase-before-push. It never writes into a watched repo.

**Tech Stack:** Python 3.11+ (stdlib only: `tomllib`, `subprocess`, `fnmatch`, `html`, `dataclasses`), git, bash, pytest.

## Global Constraints

- Python **3.11+** (uses `tomllib`). Stdlib only — no third-party runtime deps.
- Tool code lives in `project-critique/doc_digest/`; generated output in `project-critique/doc-digest.html` + `project-critique/doc-digest/YYYY-MM-DD.md`.
- **Read-only over watched repos** — the tool only runs `git log`; it writes exclusively inside `project-critique`.
- No state file — the digest is a pure function of git history + an `--as-of` date; runs are idempotent.
- All tests are deterministic and offline — build temp git repos, stamp commit dates via `GIT_COMMITTER_DATE`/`GIT_AUTHOR_DATE`, assert against a fixed `--as-of`.
- Watched projects (repo dir names): `Mentible thittam StudyBuddy_OnDemand pramana kathai-chithiram atri-sangam mambakkam-net wegofwd-llm wegofwd-video dronePrjs`.
- Commit after every task. Follow existing `portfolio_health` conventions in the same repo.

---

## File Structure

```
project-critique/doc_digest/
  doc_digest/
    __init__.py
    config.py     # DigestConfig/ProjectCfg + load_config
    paths.py      # matches_any(path, globs)
    gitlog.py     # changed_files(repo, since, until, pathspecs) -> [RawChange]
    collect.py    # collect_project(cfg, project, since, until) -> ProjectChanges
    classify.py   # build_digest(cfg, changes, since, until, generated_at) -> Digest
    render.py     # render_markdown(digest), render_html(digest)
    cli.py        # main(argv) — orchestration + file writes
  config/doc-digest.toml
  scripts/digest.sh
  tests/
    conftest.py   # temp-git-repo fixture helper
    test_config.py test_paths.py test_gitlog.py
    test_collect.py test_classify.py test_render.py test_cli.py
```

---

### Task 1: Config loader + the doc-path map

**Files:**
- Create: `doc_digest/doc_digest/__init__.py` (empty)
- Create: `doc_digest/doc_digest/config.py`
- Create: `doc_digest/config/doc-digest.toml`
- Test: `doc_digest/tests/test_config.py`

**Interfaces:**
- Produces: `ProjectCfg(name: str, include: list[str])`; `DigestConfig(base: Path, exclude: list[str], sdd_globs: list[str], doc_exts: list[str], projects: list[ProjectCfg])`; `load_config(path: str | Path) -> DigestConfig`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import textwrap, pytest
from doc_digest.config import load_config

def _write(tmp_path, body):
    p = tmp_path / "d.toml"; p.write_text(textwrap.dedent(body)); return p

def test_loads_projects_and_defaults(tmp_path):
    cfg = load_config(_write(tmp_path, """
        base = "~/hub"
        exclude = ["**/node_modules/**"]
        sdd_globs = ["docs/superpowers/**"]
        [[project]]
        name = "Mentible"
        include = ["docs", "Plans"]
    """))
    assert cfg.projects[0].name == "Mentible"
    assert cfg.projects[0].include == ["docs", "Plans"]
    assert cfg.sdd_globs == ["docs/superpowers/**"]
    assert cfg.doc_exts == [".md", ".txt", ".rst"]   # default
    assert str(cfg.base).endswith("/hub")            # ~ expanded

def test_missing_base_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(_write(tmp_path, '[[project]]\nname="x"\ninclude=["docs"]\n'))

def test_no_projects_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(_write(tmp_path, 'base="~/hub"\n'))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.config`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/config.py
from __future__ import annotations
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectCfg:
    name: str
    include: list[str]


@dataclass(frozen=True)
class DigestConfig:
    base: Path
    exclude: list[str]
    sdd_globs: list[str]
    doc_exts: list[str]
    projects: list[ProjectCfg]


def load_config(path: str | Path) -> DigestConfig:
    p = Path(path).expanduser()
    with p.open("rb") as fh:
        raw = tomllib.load(fh)
    if "base" not in raw:
        raise ValueError("doc-digest config: missing required 'base'")
    entries = raw.get("project", [])
    if not entries:
        raise ValueError("doc-digest config: no [[project]] entries")
    projects = []
    for i, e in enumerate(entries):
        if "name" not in e or "include" not in e:
            raise ValueError(f"doc-digest config: project #{i} needs name+include")
        projects.append(ProjectCfg(name=e["name"], include=list(e["include"])))
    return DigestConfig(
        base=Path(raw["base"]).expanduser(),
        exclude=list(raw.get("exclude", [])),
        sdd_globs=list(raw.get("sdd_globs", [])),
        doc_exts=list(raw.get("doc_exts", [".md", ".txt", ".rst"])),
        projects=projects,
    )
```

- [ ] **Step 4: Write the real config map**

```toml
# doc_digest/config/doc-digest.toml — per-project doc-path map for the weekly digest.
base      = "~/Documents/code/projects/AIStuff/STEM_studybuddy"
exclude   = ["**/node_modules/**", "**/.venv/**", "**/dist/**", "*-wt/**"]
sdd_globs = ["docs/superpowers/**"]
doc_exts  = [".md", ".txt", ".rst"]

[[project]]
name = "Mentible"
include = ["docs", "Plans"]
[[project]]
name = "thittam"
include = ["docs"]
[[project]]
name = "StudyBuddy_OnDemand"
include = ["docs"]
[[project]]
name = "pramana"
include = ["docs"]
[[project]]
name = "kathai-chithiram"
include = ["docs"]
[[project]]
name = "atri-sangam"
include = ["docs"]
[[project]]
name = "mambakkam-net"
include = ["docs"]
[[project]]
name = "wegofwd-llm"
include = ["README.md", "docs"]
[[project]]
name = "wegofwd-video"
include = ["README.md"]
[[project]]
name = "dronePrjs"
include = ["CLAUDE.md", "closedSpace/docs"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests). Also sanity-load the real map:
Run: `python -c "from doc_digest.config import load_config; print(len(load_config('config/doc-digest.toml').projects))"`
Expected: `10`

- [ ] **Step 6: Commit**

```bash
git add doc_digest/doc_digest/__init__.py doc_digest/doc_digest/config.py doc_digest/config/doc-digest.toml doc_digest/tests/test_config.py
git commit -m "feat(doc-digest): config loader + 10-project doc-path map"
```

---

### Task 2: Path glob matching

**Files:**
- Create: `doc_digest/doc_digest/paths.py`
- Test: `doc_digest/tests/test_paths.py`

**Interfaces:**
- Produces: `matches_any(path: str, globs: list[str]) -> bool` — `path` is repo-relative with forward slashes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths.py
from doc_digest.paths import matches_any

def test_sdd_glob_matches_nested():
    assert matches_any("docs/superpowers/plans/x.md", ["docs/superpowers/**"])

def test_non_sdd_not_matched():
    assert not matches_any("docs/adr/ADR-001.md", ["docs/superpowers/**"])

def test_exclude_nested_node_modules():
    assert matches_any("mobile/node_modules/pkg/readme.md", ["**/node_modules/**"])

def test_empty_globs_never_match():
    assert not matches_any("docs/a.md", [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_paths.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.paths`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/paths.py
from __future__ import annotations
from fnmatch import fnmatch


def matches_any(path: str, globs: list[str]) -> bool:
    """True if repo-relative `path` matches any glob. Note: fnmatch's `*`/`**`
    cross '/', so `docs/superpowers/**` matches `docs/superpowers/plans/x.md`."""
    return any(fnmatch(path, g) for g in globs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_paths.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add doc_digest/doc_digest/paths.py doc_digest/tests/test_paths.py
git commit -m "feat(doc-digest): glob path matching util"
```

---

### Task 3: Git log reader

**Files:**
- Create: `doc_digest/doc_digest/gitlog.py`
- Create: `doc_digest/tests/conftest.py`
- Test: `doc_digest/tests/test_gitlog.py`

**Interfaces:**
- Produces: `RawChange(path: str, status: str, commit_iso: str)`; `GitError(Exception)`; `changed_files(repo: Path, since: str, until: str, pathspecs: list[str]) -> list[RawChange]` — one RawChange per (file, commit) in `[since, until)` touching any pathspec, newest commit first.

- [ ] **Step 1: Write the temp-repo fixture**

```python
# tests/conftest.py
import subprocess, pytest
from pathlib import Path

@pytest.fixture
def gitrepo(tmp_path):
    """A git repo you can add dated commits to.
    Usage: gitrepo.commit({"docs/a.md": "x"}, "2026-08-04T09:00:00")
    """
    root = tmp_path / "repo"; root.mkdir()
    def run(*args, when=None):
        env = None
        if when:
            import os
            env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True, text=True, env=env)
    run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
    class Repo:
        path = root
        def commit(self, files, when, msg="c", delete=None):
            for rel, body in files.items():
                f = root / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(body)
                run("add", rel)
            for rel in (delete or []):
                run("rm", "-q", rel)
            run("commit", "-q", "-m", msg, when=when)
    return Repo()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_gitlog.py
from doc_digest.gitlog import changed_files, GitError
import pytest
from pathlib import Path

def test_in_window_changes_captured(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-08-04T09:00:00")
    gitrepo.commit({"docs/a.md": "2", "docs/b.md": "1"}, "2026-08-06T09:00:00")
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    paths = sorted(c.path for c in out)
    assert paths == ["docs/a.md", "docs/b.md"]        # only the 08-06 commit is in-window
    assert all(c.commit_iso.startswith("2026-08-06") for c in out)

def test_out_of_window_ignored(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-07-01T09:00:00")
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    assert out == []

def test_status_letter(gitrepo):
    gitrepo.commit({"docs/a.md": "1"}, "2026-08-06T09:00:00")   # A
    out = changed_files(gitrepo.path, "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
    assert out[0].status == "A"

def test_bad_repo_raises():
    with pytest.raises(GitError):
        changed_files(Path("/nonexistent/repo"), "2026-08-05T00:00:00", "2026-08-07T00:00:00", ["docs"])
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_gitlog.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.gitlog`)

- [ ] **Step 4: Write minimal implementation**

```python
# doc_digest/gitlog.py
from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path

_SEP = "\x00"


class GitError(Exception):
    pass


@dataclass(frozen=True)
class RawChange:
    path: str
    status: str        # first char: A/M/D
    commit_iso: str    # committer date, ISO 8601


def changed_files(repo: Path, since: str, until: str, pathspecs: list[str]) -> list[RawChange]:
    cmd = ["git", "-C", str(repo), "log",
           f"--since={since}", f"--until={until}",
           "--name-status", "--no-renames", f"--pretty=format:C{_SEP}%cI",
           "--", *pathspecs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git log failed in {repo}")
    out: list[RawChange] = []
    cur_iso = ""
    for line in proc.stdout.splitlines():
        if line.startswith("C" + _SEP):
            cur_iso = line.split(_SEP, 1)[1]
        elif line.strip():
            cols = line.split("\t")
            out.append(RawChange(path=cols[-1], status=cols[0][0], commit_iso=cur_iso))
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_gitlog.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add doc_digest/doc_digest/gitlog.py doc_digest/tests/conftest.py doc_digest/tests/test_gitlog.py
git commit -m "feat(doc-digest): windowed git-log reader + temp-repo test fixture"
```

---

### Task 4: Per-project collection

**Files:**
- Create: `doc_digest/doc_digest/collect.py`
- Test: `doc_digest/tests/test_collect.py`

**Interfaces:**
- Consumes: `DigestConfig`, `ProjectCfg` (Task 1); `changed_files`, `GitError` (Task 3).
- Produces: `DocFile(path: str, change: str, commits: int, last_date: str)`; `ProjectChanges(name: str, status: str, files: list[DocFile], error: str | None)`; `collect_project(cfg: DigestConfig, project: ProjectCfg, since: str, until: str) -> ProjectChanges`. `status` ∈ `{"ok","missing","error"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_collect.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_collect.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.collect`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/collect.py
from __future__ import annotations
from dataclasses import dataclass

from doc_digest.config import DigestConfig, ProjectCfg
from doc_digest.gitlog import changed_files, GitError
from doc_digest.paths import matches_any


@dataclass
class DocFile:
    path: str
    change: str
    commits: int
    last_date: str


@dataclass
class ProjectChanges:
    name: str
    status: str
    files: list[DocFile]
    error: str | None = None


def collect_project(cfg: DigestConfig, project: ProjectCfg, since: str, until: str) -> ProjectChanges:
    repo = cfg.base / project.name
    if not (repo / ".git").exists():
        return ProjectChanges(project.name, "missing", [], None)
    try:
        raws = changed_files(repo, since, until, project.include)
    except GitError as e:
        return ProjectChanges(project.name, "error", [], str(e))
    agg: dict[str, DocFile] = {}
    for r in raws:  # newest-first: first sighting is the latest change
        if not any(r.path.endswith(ext) for ext in cfg.doc_exts):
            continue
        if matches_any(r.path, cfg.exclude):
            continue
        cur = agg.get(r.path)
        if cur is None:
            agg[r.path] = DocFile(r.path, r.status, 1, r.commit_iso)
        else:
            cur.commits += 1
    return ProjectChanges(project.name, "ok", sorted(agg.values(), key=lambda f: f.path), None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_collect.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doc_digest/doc_digest/collect.py doc_digest/tests/test_collect.py
git commit -m "feat(doc-digest): per-project doc-change collection (filter+dedup)"
```

---

### Task 5: Digest assembly (two-tier + ordering)

**Files:**
- Create: `doc_digest/doc_digest/classify.py`
- Test: `doc_digest/tests/test_classify.py`

**Interfaces:**
- Consumes: `DigestConfig` (Task 1); `ProjectChanges`, `DocFile` (Task 4); `matches_any` (Task 2).
- Produces: `ProjectDigest(name, status, headline: list[DocFile], sdd_files: int, sdd_commits: int, error)`; `Digest(window_start, window_end, generated_at, projects: list[ProjectDigest], totals: dict)`; `build_digest(cfg: DigestConfig, changes: list[ProjectChanges], since: str, until: str, generated_at: str) -> Digest`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_classify.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_classify.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.classify`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/classify.py
from __future__ import annotations
from dataclasses import dataclass

from doc_digest.config import DigestConfig
from doc_digest.collect import ProjectChanges, DocFile
from doc_digest.paths import matches_any


@dataclass
class ProjectDigest:
    name: str
    status: str
    headline: list[DocFile]
    sdd_files: int
    sdd_commits: int
    error: str | None = None


@dataclass
class Digest:
    window_start: str
    window_end: str
    generated_at: str
    projects: list[ProjectDigest]
    totals: dict


def build_digest(cfg: DigestConfig, changes: list[ProjectChanges],
                 since: str, until: str, generated_at: str) -> Digest:
    pds: list[ProjectDigest] = []
    for ch in changes:
        headline, sdd_files, sdd_commits = [], 0, 0
        for f in ch.files:
            if matches_any(f.path, cfg.sdd_globs):
                sdd_files += 1
                sdd_commits += f.commits
            else:
                headline.append(f)
        pds.append(ProjectDigest(ch.name, ch.status, headline, sdd_files, sdd_commits, ch.error))

    def rank(pd: ProjectDigest):
        if pd.status in ("missing", "error"):
            return (3, 0)
        if pd.headline:
            return (0, -len(pd.headline))
        if pd.sdd_files:
            return (1, 0)
        return (2, 0)

    pds.sort(key=rank)
    totals = {
        "projects": len(pds),
        "with_headline": sum(1 for p in pds if p.headline),
        "quiet": sum(1 for p in pds if p.status == "ok" and not p.headline and not p.sdd_files),
        "errors": sum(1 for p in pds if p.status in ("missing", "error")),
    }
    return Digest(since, until, generated_at, pds, totals)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_classify.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doc_digest/doc_digest/classify.py doc_digest/tests/test_classify.py
git commit -m "feat(doc-digest): two-tier digest assembly + ordering"
```

---

### Task 6: Rendering (markdown + HTML)

**Files:**
- Create: `doc_digest/doc_digest/render.py`
- Test: `doc_digest/tests/test_render.py`

**Interfaces:**
- Consumes: `Digest`, `ProjectDigest` (Task 5); `DocFile` (Task 4).
- Produces: `render_markdown(digest: Digest) -> str`; `render_html(digest: Digest) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_render.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.render`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/render.py
from __future__ import annotations
from html import escape

from doc_digest.classify import Digest, ProjectDigest

_CHANGE = {"A": "added", "M": "modified", "D": "deleted"}


def _date(iso: str) -> str:
    return iso[:10] if iso else ""


def _headline_cell(pd: ProjectDigest) -> str:
    if pd.status == "missing":
        return "MISSING (run github_checkout.sh)"
    if pd.status == "error":
        return f"ERROR: {pd.error}"
    if not pd.headline:
        return "—"
    return ", ".join(f"{f.path.split('/')[-1]} ({f.change})" for f in pd.headline)


def _sdd_cell(pd: ProjectDigest) -> str:
    if pd.sdd_files == 0:
        return "—"
    return f"{pd.sdd_files} files / {pd.sdd_commits} commits"


def render_markdown(digest: Digest) -> str:
    t = digest.totals
    lines = [
        f"# Weekly Doc Digest — {_date(digest.window_end)}   "
        f"(window: {_date(digest.window_start)} → {_date(digest.window_end)})",
        f"_Generated {digest.generated_at} · {t['projects']} projects · "
        f"{t['with_headline']} with headline changes · {t['quiet']} quiet · {t['errors']} missing/error_",
        "",
        "| Project | Headline docs | SDD activity |",
        "|---|---|---|",
    ]
    for pd in digest.projects:
        lines.append(f"| {pd.name} | {_headline_cell(pd)} | {_sdd_cell(pd)} |")
    lines += ["", "## Details"]
    for pd in digest.projects:
        if pd.status != "ok" or not (pd.headline or pd.sdd_files):
            continue
        lines.append(f"### {pd.name} — {len(pd.headline)} headline, {pd.sdd_files} SDD")
        for f in pd.headline:
            lines.append(f"- `{f.path}` — {_CHANGE.get(f.change, f.change)}, "
                         f"{f.commits} commit(s), last {_date(f.last_date)}")
    return "\n".join(lines) + "\n"


def render_html(digest: Digest) -> str:
    t = digest.totals
    rows = []
    for pd in digest.projects:
        cls = "miss" if pd.status in ("missing", "error") else ("head" if pd.headline else "quiet")
        rows.append(
            f'<tr class="{cls}"><td>{escape(pd.name)}</td>'
            f"<td>{escape(_headline_cell(pd))}</td><td>{escape(_sdd_cell(pd))}</td></tr>"
        )
    style = (
        "body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #8884;padding:.4rem .6rem;text-align:left}"
        "tr.quiet{opacity:.55}tr.miss{color:#b00}"
        "@media(prefers-color-scheme:dark){body{background:#111;color:#eee}tr.miss{color:#f88}}"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Weekly Doc Digest — {escape(_date(digest.window_end))}</title>"
        f"<style>{style}</style></head><body>"
        f"<h1>Weekly Doc Digest — {escape(_date(digest.window_end))}</h1>"
        f"<p>Window {escape(_date(digest.window_start))} → {escape(_date(digest.window_end))} · "
        f"generated {escape(digest.generated_at)} · {t['with_headline']} with headline changes · "
        f"{t['quiet']} quiet · {t['errors']} missing/error</p>"
        "<table><tr><th>Project</th><th>Headline docs</th><th>SDD activity</th></tr>"
        + "".join(rows) + "</table></body></html>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_render.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doc_digest/doc_digest/render.py doc_digest/tests/test_render.py
git commit -m "feat(doc-digest): markdown + self-contained HTML rendering"
```

---

### Task 7: CLI orchestration

**Files:**
- Create: `doc_digest/doc_digest/cli.py`
- Test: `doc_digest/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config` (T1), `collect_project` (T4), `build_digest` (T5), `render_markdown`/`render_html` (T6).
- Produces: `main(argv: list[str] | None = None) -> int`. Args: `--config` (required), `--base` (override), `--since-days` (default 7), `--as-of` (ISO date/datetime, default now), `--out-md` (required), `--out-html` (required). Computes `until = as_of`, `since = as_of − since_days`, loops projects, writes both files, returns 0.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd doc_digest && python -m pytest tests/test_cli.py -v`
Expected: FAIL (`ModuleNotFoundError: doc_digest.cli`)

- [ ] **Step 3: Write minimal implementation**

```python
# doc_digest/cli.py
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from doc_digest.config import load_config
from doc_digest.collect import collect_project
from doc_digest.classify import build_digest
from doc_digest.render import render_markdown, render_html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="doc_digest")
    ap.add_argument("--config", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--since-days", type=int, default=7)
    ap.add_argument("--as-of", default=None, help="ISO date/datetime; default now")
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-html", required=True)
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if args.base:
        cfg = type(cfg)(base=Path(args.base).expanduser(), exclude=cfg.exclude,
                        sdd_globs=cfg.sdd_globs, doc_exts=cfg.doc_exts, projects=cfg.projects)

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now()
    since = as_of - timedelta(days=args.since_days)
    since_s, until_s = since.isoformat(), as_of.isoformat()
    generated = as_of.strftime("%Y-%m-%d %H:%M")

    changes = [collect_project(cfg, p, since_s, until_s) for p in cfg.projects]
    digest = build_digest(cfg, changes, since_s, until_s, generated)

    Path(args.out_md).expanduser().write_text(render_markdown(digest), encoding="utf-8")
    Path(args.out_html).expanduser().write_text(render_html(digest), encoding="utf-8")
    print(f"doc-digest: {digest.totals['with_headline']} projects with headline changes "
          f"→ {args.out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd doc_digest && python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run the FULL suite + a real dry run**

Run: `cd doc_digest && python -m pytest -q`
Expected: all tests pass, output pristine.
Run: `python -m doc_digest.cli --config config/doc-digest.toml --as-of "$(date -Iseconds)" --out-md /tmp/dd.md --out-html /tmp/dd.html && echo OK`
Expected: prints the summary line + OK; `/tmp/dd.md` lists real recent doc changes across the 10 projects.

- [ ] **Step 6: Commit**

```bash
git add doc_digest/doc_digest/cli.py doc_digest/tests/test_cli.py
git commit -m "feat(doc-digest): CLI orchestration (config→collect→digest→render→write)"
```

---

### Task 8: Weekly cron wrapper + install

**Files:**
- Create: `doc_digest/scripts/digest.sh`
- Create: `doc_digest/README.md` (usage + cron line)

**Interfaces:**
- Consumes: `doc_digest.cli` (T7); the hardened push pattern from `portfolio_health/scripts/refresh.sh`.
- Produces: an executable wrapper that writes `project-critique/doc-digest.html` + `project-critique/doc-digest/<date>.md`, then commits + rebase-pushes.

- [ ] **Step 1: Write the wrapper**

```bash
#!/usr/bin/env bash
# digest.sh — weekly wrapper for the doc digest. Reads the 10 watched repos
# (read-only), writes the report into project-critique, commits + rebase-pushes.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"        # project-critique
BASE="${PORTFOLIO_ROOT:-$HOME/Documents/code/projects/AIStuff/STEM_studybuddy}"
PY="${PYTHON:-$ROOT/portfolio_health/.venv/bin/python}"; [ -x "$PY" ] || PY=python3
URL="https://github.com/wegofwd2020-hub/project-critique.git"
LOG_DIR="$HOME/.local/share/doc-digest"; mkdir -p "$LOG_DIR" "$ROOT/doc-digest"
DATE="$(date -u +%Y-%m-%d)"

# Guarded fetch of watched repos (ff-only; skip dirty/detached/non-github) so the
# digest is correct even if the daily portfolio refresh didn't run.
for name in Mentible thittam StudyBuddy_OnDemand pramana kathai-chithiram \
            atri-sangam mambakkam-net wegofwd-llm wegofwd-video dronePrjs; do
  d="$BASE/$name"; [ -e "$d/.git" ] || continue
  [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ] && continue
  br="$(git -C "$d" symbolic-ref --quiet --short HEAD 2>/dev/null)" || continue
  url="$(git -C "$d" remote get-url origin 2>/dev/null)" || continue
  https="$(printf '%s' "$url" | sed -E 's#^git@github\.com:#https://github.com/#')"
  case "$https" in https://github.com/*) git -C "$d" pull --ff-only --quiet "$https" "$br" 2>/dev/null || true ;; esac
done

"$PY" -m doc_digest.cli \
    --config "$ROOT/doc_digest/config/doc-digest.toml" \
    --as-of "$(date -Iseconds)" --since-days 7 \
    --out-md "$ROOT/doc-digest/$DATE.md" \
    --out-html "$ROOT/doc-digest.html" || exit 1

cd "$ROOT"
if ! git diff --quiet doc-digest.html "doc-digest/$DATE.md" 2>/dev/null || \
   [ -n "$(git status --porcelain "doc-digest/$DATE.md")" ]; then
  git add doc-digest.html "doc-digest/$DATE.md"
  git -c commit.gpgsign=false commit -m "chore(doc-digest): weekly digest $DATE"
  if ! git -c rebase.autoStash=false pull --rebase --quiet "$URL" main; then
    git rebase --abort 2>/dev/null || true
    echo "doc-digest: rebase conflict — commit kept local, push skipped"; exit 1
  fi
  git push "$URL" HEAD:main
fi
```

- [ ] **Step 2: Write the README (usage + cron)**

````markdown
# doc_digest — weekly documentation-change digest

Read-only weekly report of what docs changed across 10 portfolio projects.
Writes `project-critique/doc-digest.html` + `doc-digest/<date>.md`. Never writes
into a watched repo. Design: `docs/superpowers/specs/2026-08-05-weekly-doc-digest-design.md`.

## Run manually
```bash
python -m doc_digest.cli --config doc_digest/config/doc-digest.toml \
  --out-md /tmp/dd.md --out-html /tmp/dd.html
```

## Install weekly cron (Mon 07:45, after the daily portfolio refresh)
```bash
(crontab -l 2>/dev/null; \
 echo "45 7 * * 1 $PWD/doc_digest/scripts/digest.sh >> $HOME/.local/share/doc-digest/digest.log 2>&1") | crontab -
```
````

- [ ] **Step 3: Validate the wrapper**

Run: `chmod +x doc_digest/scripts/digest.sh && bash -n doc_digest/scripts/digest.sh && echo "syntax OK"`
Expected: `syntax OK`
Run (dry, no commit — comment out the git block or run on a scratch branch): confirm it writes `doc-digest.html` + `doc-digest/<date>.md` with real content.

- [ ] **Step 4: Commit**

```bash
git add doc_digest/scripts/digest.sh doc_digest/README.md
git commit -m "feat(doc-digest): weekly cron wrapper + usage README"
```

- [ ] **Step 5: Install the cron (operator step, after review)**

Run the crontab line from the README. Verify: `crontab -l | grep doc-digest`.

---

## Definition of Done

- Tasks 1–8 committed; `cd doc_digest && python -m pytest -q` all green, output pristine.
- A manual run produces a correct `doc-digest.html` + `doc-digest/<date>.md` for the current window.
- `digest.sh` passes `bash -n`; a dry run writes both artifacts with real content.
- Weekly cron installed (`45 7 * * 1`), logging to `~/.local/share/doc-digest/digest.log`.
- No watched repo is modified; `github_checkout.sh` / `github_update.sh` untouched.
