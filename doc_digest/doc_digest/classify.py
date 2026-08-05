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
