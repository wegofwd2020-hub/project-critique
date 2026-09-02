# Documentation standards — WeGoFwd2020 product docs

## Doc-meta table (required on every product document)

Every **product document** — the four-lens set per product (`<product>-critique.md`,
`<product>-development-pattern.md`, `<product>-practices.md`, and the private
`<product>-cost.md`) — carries a small metadata table immediately after its H1
title, delimited by HTML markers so a script can refresh it in place:

```
<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/<Repo>` |
| Branch | `main` |
| Git commit | `<short-sha>` (as of <YYYY-MM-DD>) |
| Product version | <release version, or — if commit-based> |
| Doc updated | <YYYY-MM-DD> |
| Last deployed | <date-time, or "not deployed — <why>"> |
<!-- doc-meta:end -->
```

**Field semantics**
- **Git commit** — the product repo's `origin/main` commit the doc *reflects* (what
  it was measured against), with that commit's date. This is the definitive "git
  version". Products with no release tag are identified by this alone.
- **Branch** — the ref the doc measures; house discipline is `origin/main` (see
  `verify-from-repos`). A doc measured on a feature branch names that branch.
- **Product version** — the product's real release version where one exists (e.g.
  Mentible `0.2.63` from `mobile/app.json`). Git *tags* are unreliable for this
  (some are demo markers), so it is read from the authoritative version file, not
  `git describe`. `—` when the product is commit-based (e.g. StudyBuddy OnDemand).
- **Doc updated** — the date this doc was last refreshed.
- **Last deployed** — when the *product* was last deployed to a real environment,
  with date-time. **Not derivable from git** — a manual field the maintainer sets;
  `not deployed — <reason>` for pre-launch products. The stamp script preserves an
  existing value.

## Stamping — `scripts/stamp_doc.py`

Auto-fills the git-derived fields (commit / branch / version / doc-updated) from the
*product's* `origin/main`; preserves the manual `Last deployed` value.

```
scripts/stamp_doc.py <doc.md> [<doc2.md> ...]        # stamp / refresh in place
scripts/stamp_doc.py --commit=<sha> <doc.md>         # pin to the commit the doc measured
                                                     #   (use when origin/main has moved past it)
scripts/stamp_doc.py --check <doc.md>                # CI: non-zero if table missing/stale-commit
```

The product repo is inferred from the doc's filename prefix (mapping in the script;
add a row there when a new product joins the suite). The script works on docs in any
repo (public `project-critique` or private `wegofwd-private-docs`) — it reads the
*product* repo's git regardless of where the doc file lives.

## Workflow

Run `stamp_doc.py` as the **final step of any product-doc update**, so the table
captures the product commit + date at the moment of that update. Pass `--commit=<sha>`
to match the exact commit the body was measured against when `origin/main` has already
advanced (products like StudyBuddy commit daily). Then set/refresh `Last deployed`
by hand if the product's deploy state changed.

`--check` mode is suitable for a pre-commit hook or CI gate: it fails if a product doc
is missing the table or its commit is stale versus the product's current `origin/main`.
