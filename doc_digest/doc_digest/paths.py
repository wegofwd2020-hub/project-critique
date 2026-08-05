from __future__ import annotations
from fnmatch import fnmatch


def matches_any(path: str, globs: list[str]) -> bool:
    """True if repo-relative `path` matches any glob. Note: fnmatch's `*`/`**`
    cross '/', so `docs/superpowers/**` matches `docs/superpowers/plans/x.md`."""
    return any(fnmatch(path, g) for g in globs)
