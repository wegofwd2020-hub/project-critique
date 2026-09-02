#!/usr/bin/env python3
"""Stamp (or refresh) the standard doc-meta table on a product document.

Every product document carries a small metadata table pinning WHICH product
commit the doc reflects, on which branch, the product's release version (if
tagged), when the doc was last updated, and when the product was last deployed.

Git-derived fields (commit / branch / version / doc-updated) are auto-filled
from the *product's* `origin/main`. "Last deployed" is NOT in git, so it is a
manual field: an existing value is preserved; a new stamp writes a TODO the
maintainer fills in.

Usage:
    scripts/stamp_doc.py <doc.md> [<doc2.md> ...]
    scripts/stamp_doc.py --check <doc.md>     # non-zero exit if missing/stale-commit

The product repo is inferred from the doc's filename prefix (see PRODUCT_REPOS).
Repos live as siblings under STEM_studybuddy/. The table is delimited by
<!-- doc-meta:start --> / <!-- doc-meta:end --> and inserted right after the
first H1 if absent, else replaced in place.
"""
from __future__ import annotations
import datetime as _dt
import pathlib
import re
import subprocess
import sys

# STEM_studybuddy/ — two levels up from this script (project-critique/scripts/).
STEM = pathlib.Path(__file__).resolve().parents[2]

# doc filename prefix -> product repo dir (relative to STEM). Longest prefix wins.
PRODUCT_REPOS = {
    "studybuddy": "StudyBuddy_OnDemand",
    "mentible": "Mentible",
    "thittam": "thittam",
    "dronePrjs": "dronePrjs",
    "MarketingTools": "MarketingTools",
    "atri-sangam": "atri-sangam",
    "wegofwd-llm": "wegofwd-llm",
    "wegofwd-video": "wegofwd-video",
    "agastya": "agastya",
    "wegofwd-expenses": "wegofwd-expenses",
    "local-watch": "local_watch",
    "local_watch": "local_watch",
    "timesheet": "wegofwd-hub",  # timesheet is a Django app inside wegofwd-hub
}

# Where a product's real release version lives (origin/main path, JSON key or regex).
# Git tags are unreliable here (StudyBuddy tags are demo markers; Mentible's
# app version isn't a tag), so read the authoritative version FILE. Products with
# no meaningful release version resolve to "—" (commit-based).
VERSION_SOURCES = {
    "Mentible": ("mobile/app.json", "json:version"),
}

START = "<!-- doc-meta:start -->"
END = "<!-- doc-meta:end -->"
DEPLOY_TODO = "TODO — set last deployment date-time (not in git)"


def _repo_for(doc: pathlib.Path) -> pathlib.Path | None:
    name = doc.name
    for prefix in sorted(PRODUCT_REPOS, key=len, reverse=True):
        if name.startswith(prefix):
            return STEM / PRODUCT_REPOS[prefix]
    return None


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    ).stdout.strip()


def _resolve_version(repo: pathlib.Path, ref: str) -> str:
    src = VERSION_SOURCES.get(repo.name)
    if not src:
        return "—  (commit-based; no release version)"
    path, how = src
    blob = _git(repo, "show", f"{ref}:{path}")
    if not blob:
        return "—  (version file not found)"
    if how.startswith("json:"):
        key = how.split(":", 1)[1]
        m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]+)"', blob)
        return m.group(1) if m else "—"
    m = re.search(how, blob)  # treat `how` as a regex with group 1
    return m.group(1) if m else "—"


def _product_info(repo: pathlib.Path, commit_override: str | None = None) -> dict:
    # measure the doc against origin/main (the published state), per house discipline
    branch = "main"
    ref = "origin/main"
    _git(repo, "fetch", "-q", "origin")  # best-effort; offline is fine
    if commit_override:
        commit = _git(repo, "rev-parse", "--short", commit_override) or commit_override
        when = _git(repo, "log", "-1", "--format=%ci", commit_override)[:10] or "unknown"
    else:
        commit = _git(repo, "rev-parse", "--short", ref) or "unknown"
        when = _git(repo, "log", "-1", "--format=%ci", ref)[:10] or "unknown"
    version = _resolve_version(repo, commit_override or ref)
    return {"repo": repo.name, "branch": branch, "commit": commit,
            "version": version, "commit_date": when}


def _existing_deploy(text: str) -> str | None:
    m = re.search(r"\|\s*Last deployed\s*\|\s*(.+?)\s*\|", text)
    return m.group(1).strip() if m else None


def _table(info: dict, deployed: str, doc_updated: str) -> str:
    return "\n".join([
        START,
        "| Field | Value |",
        "|---|---|",
        f"| Product repo | `wegofwd2020-hub/{info['repo']}` |",
        f"| Branch | `{info['branch']}` |",
        f"| Git commit | `{info['commit']}` (as of {info['commit_date']}) |",
        f"| Product version | {info['version']} |",
        f"| Doc updated | {doc_updated} |",
        f"| Last deployed | {deployed} |",
        END,
    ])


def stamp(doc: pathlib.Path, check: bool = False, commit_override: str | None = None) -> bool:
    repo = _repo_for(doc)
    if repo is None or not repo.exists():
        print(f"SKIP {doc.name}: no product repo mapped (prefix unknown or repo missing)")
        return False
    text = doc.read_text()
    info = _product_info(repo, commit_override)
    today = _dt.date.today().isoformat()

    if check:
        m = re.search(re.escape(START) + r".*?" + re.escape(END), text, re.S)
        if not m:
            print(f"MISSING doc-meta table: {doc.name}")
            return False
        if info["commit"] not in m.group(0):
            print(f"STALE commit in {doc.name}: doc-meta not at {info['commit']}")
            return False
        print(f"OK {doc.name} @ {info['commit']}")
        return True

    deployed = _existing_deploy(text) or DEPLOY_TODO
    block = _table(info, deployed, today)

    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
    else:
        # insert after the first H1 (`# Title`) line; else at top
        lines = text.splitlines(keepends=True)
        idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), -1)
        insert_at = idx + 1 if idx >= 0 else 0
        lines.insert(insert_at, "\n" + block + "\n")
        new = "".join(lines)

    if new != text:
        doc.write_text(new)
        print(f"stamped {doc.name}: {info['repo']}@{info['commit']} ({info['version']}), "
              f"doc {today}, deploy='{deployed}'")
    else:
        print(f"unchanged {doc.name}")
    return True


def main(argv: list[str]) -> int:
    check = "--check" in argv
    commit_override = None
    for a in argv:
        if a.startswith("--commit="):
            commit_override = a.split("=", 1)[1]
    docs = [a for a in argv if not a.startswith("--")]
    if not docs:
        print(__doc__)
        return 2
    ok = all(stamp(pathlib.Path(d).resolve(), check=check, commit_override=commit_override)
             for d in docs)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
