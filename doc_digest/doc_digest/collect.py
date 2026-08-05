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
