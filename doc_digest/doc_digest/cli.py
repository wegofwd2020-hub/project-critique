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
