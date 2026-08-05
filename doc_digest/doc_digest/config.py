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
