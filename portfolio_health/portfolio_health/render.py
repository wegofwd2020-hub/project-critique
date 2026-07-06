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
                 f'<span>{_DOT.get(pr["health"]["status"], "")} {escape(pr["health"]["status"])}</span>'
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
