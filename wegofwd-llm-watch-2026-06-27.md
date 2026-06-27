# wegofwd-llm — Watch Report 2026-06-27

**Triggered by:** GitHub Actions watch workflow ([wegofwd-llm/.github/workflows/watch.yml](https://github.com/wegofwd2020-hub/wegofwd-llm/blob/main/.github/workflows/watch.yml))
**Baseline (last reviewed):** `4e0d26d79a6846aab06fd600ebd671c665ca5ad5`
**Current HEAD:** `f01d913` (`f01d9135a0dad53e8b715e2838d63f30d8f538d9`)
**Commit count in window:** 8
**Current test count:** 56 `def test_` across `tests/`
**Current source LOC:** 918 (excl. `__init__.py`)

**🔔 Version bump detected: `0.1.2` → `0.2.0`** — per `wegofwd-llm-critique.md` §8, every version bump triggers a full re-critique (re-run sections 1–6, refresh the Snapshot table).

## Commits since baseline

```
f01d913 Merge pull request #3 from wegofwd2020-hub/docs/shared-service-diagram
b47aff6 docs: add canonical shared-services architecture diagram
6aaa300 Merge pull request #2 from wegofwd2020-hub/feat/adr-015-content-trust-manifest
0a1e567 chore(release): bump version to 0.2.0 for Content Trust Manifest
c98ca13 Merge branch 'main' into feat/adr-015-content-trust-manifest
2847a1a Merge pull request #1 from wegofwd2020-hub/fix/typed-anthropic-errors
593f130 fix(anthropic): map SDK exceptions to typed seam errors → v0.1.3
581ed5a feat(trust): Content Trust Manifest — seam emits provenance+validation (ADR-015)
```

## Files changed (diffstat)

```
 README.md                             |   8 ++
 docs/shared_service.drawio            |  37 ++++++++
 pyproject.toml                        |   2 +-
 schema/content-trust-manifest.v1.json |  83 ++++++++++++++++
 tests/test_anthropic_native.py        |  64 ++++++++++++-
 tests/test_trust.py                   |  80 ++++++++++++++++
 wegofwd_llm/__init__.py               |  24 ++++-
 wegofwd_llm/anthropic_native.py       |  49 +++++++++-
 wegofwd_llm/trust.py                  | 174 ++++++++++++++++++++++++++++++++++
 9 files changed, 513 insertions(+), 8 deletions(-)
```

## What to do with this report

- **If it's a version bump or touches `contract.py` / `registry.py` / `errors.py`:** trigger a full re-critique — re-run `wegofwd-llm-critique.md` §1–§7 against the new HEAD. Update the Snapshot table.
- **If it only touches `tests/` or `pyproject.toml` cosmetic fields:** update test/LOC numbers in the critique's Snapshot table only; no §7 re-rank needed.
- **If the change is large enough that the §7 priority actions move:** also refresh the README `### wegofwd-llm (shared LLM seam)` Quick Summary block.
- **If a consumer of wegofwd-llm (StudyBuddy_OnDemand / SelfLearner / Kathai Chithiram) needs to bump its pin to ride this change:** add a note to the consumer's next critique-refresh delta noting which behaviour change is now exposed.

Merging this PR advances `wegofwd-llm-last-reviewed.txt` to `f01d9135a0dad53e8b715e2838d63f30d8f538d9` — the next weekly watch will measure from this commit forward.

---

*Generated automatically by `wegofwd-llm/.github/workflows/watch.yml`. The critique itself is human/Claude-authored; this report is just the change-detection prompt.*
