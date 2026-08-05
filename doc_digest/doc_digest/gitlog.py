from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Unit Separator (ASCII 0x1f): unambiguous field marker that never appears in
# git's ISO dates or file paths, and — unlike NUL — is legal in a subprocess argv.
_SEP = "\x1f"


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
