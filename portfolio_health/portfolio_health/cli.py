"""CLI: read config, collect the portfolio, write portfolio.json + portfolio.html."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from portfolio_health.collect import collect
from portfolio_health.render import build_html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="portfolio-health")
    ap.add_argument("--config", required=True)
    ap.add_argument("--json", required=True, dest="json_out")
    ap.add_argument("--html", required=True, dest="html_out")
    ap.add_argument("--root", default=None, help="override config scan.root")
    ap.add_argument("--reviewed-dir", default=None, dest="reviewed_dir",
                    help="dir holding <repo>-last-reviewed.txt anchors "
                         "(default: the config file's repo root)")
    args = ap.parse_args(argv)
    try:
        with open(args.config, "rb") as fh:
            cfg = tomllib.load(fh).get("scan", {})
        root = args.root or cfg.get("root", ".")
        # Anchors live in the project-critique root; the config sits at
        # <project-critique>/config/portfolio.toml, so its parent's parent is
        # that root unless overridden.
        reviewed_dir = (Path(args.reviewed_dir).expanduser() if args.reviewed_dir
                        else Path(args.config).resolve().parent.parent)
        portfolio = collect(Path(root).expanduser(),
                            exclude=cfg.get("exclude", []),
                            exploratory_stages=cfg.get("exploratory_stages", ["unknown"]),
                            reviewed_dir=reviewed_dir)
        Path(args.json_out).write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
        Path(args.html_out).write_text(build_html(portfolio), encoding="utf-8")
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"portfolio-health: {e}", file=sys.stderr)
        return 1
    s = portfolio["summary"]
    st = s["staleness"]
    print(f"portfolio-health: {s['projects']} repos "
          f"(🟢{s['health']['green']} 🟡{s['health']['yellow']} 🔴{s['health']['red']}) "
          f"· reviews {st['fresh']} fresh / {st['stale']} stale / {st['unknown']} unknown "
          f"→ {args.html_out}")
    return 0
