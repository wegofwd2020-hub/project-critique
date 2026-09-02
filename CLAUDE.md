# project-critique — working notes for Claude

`project-critique` is the WeGoFwd2020 portfolio-critique hub: docs only (no app code)
— four-lens per-product critiques (`<product>-critique.md` · `-development-pattern.md`
· `-practices.md`; the private `-cost.md` lives in `wegofwd-private-docs`) plus
cross-cutting docs (`README.md`, `PRODUCT_CATALOG.md`) and drawio diagrams.

## Doc-meta table — REQUIRED on every product-doc update

Every product document carries a doc-meta table (git commit · branch · product
version · doc-updated · last-deployed) right after its H1 — see `DOC_STANDARDS.md`.

**Whenever you update a product doc, refresh its doc-meta table as the final step:**

```
scripts/stamp_doc.py <doc.md>                 # auto-fills commit/branch/version/date
scripts/stamp_doc.py --commit=<sha> <doc.md>  # pin to the measured commit if origin/main moved past it
```

The `Last deployed` field is manual (not in git) — set it by hand when the product's
deploy state changes; the script preserves it otherwise. This applies to docs in the
private `wegofwd-private-docs` repo too (cost docs) — the script reads the product
repo's git regardless of where the doc file lives.

## House discipline
- Measure products against `origin/main`, not the working tree (checkouts drift; see
  the `verify-from-repos` practice). `git show origin/main:<path>` / `git log origin/main`.
- Cost docs are **private** (`wegofwd-private-docs`) — never write `*-cost.md` or
  per-engineer rate numbers into this public repo.
