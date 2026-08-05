# doc_digest — weekly documentation-change digest

Read-only weekly report of what docs changed across 10 portfolio projects.
Writes `project-critique/doc-digest.html` + `doc-digest/<date>.md`. Never writes
into a watched repo. Design: `docs/superpowers/specs/2026-08-05-weekly-doc-digest-design.md`.

## Run manually
```bash
cd doc_digest
python3 -m doc_digest.cli --config config/doc-digest.toml \
  --out-md /tmp/dd.md --out-html /tmp/dd.html
```

(`python3` must be 3.11+ for `tomllib`; the tool is stdlib-only. Tests use a
local `.venv` with pytest — see below.)

## Run the tests
```bash
cd doc_digest
python3 -m venv .venv && .venv/bin/python -m pip install pytest   # first time only
.venv/bin/python -m pytest -q
```

## Install weekly cron (Mon 07:45, after the daily portfolio refresh)
```bash
(crontab -l 2>/dev/null; \
 echo "45 7 * * 1 $PWD/doc_digest/scripts/digest.sh >> $HOME/.local/share/doc-digest/digest.log 2>&1") | crontab -
```

The wrapper reads the 10 repos under `$PORTFOLIO_ROOT`
(default `~/Documents/AIStuff/wegofwd2020-hub`), regenerates the report, and
commits it to `project-critique` main with rebase-before-push.
