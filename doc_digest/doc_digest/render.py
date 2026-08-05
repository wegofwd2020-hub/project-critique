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
