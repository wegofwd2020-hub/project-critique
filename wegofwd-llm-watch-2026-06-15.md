# wegofwd-llm — Watch Report 2026-06-15

**Triggered by:** GitHub Actions watch workflow ([wegofwd-llm/.github/workflows/watch.yml](https://github.com/wegofwd2020-hub/wegofwd-llm/blob/main/.github/workflows/watch.yml))
**Baseline (last reviewed):** `4e0d26d79a6846aab06fd600ebd671c665ca5ad5`
**Current HEAD:** `2847a1a` (`2847a1abb311446bb433996e76d2bcbd3d59be5f`)
**Commit count in window:** 2
**Current test count:** 50 `def test_` across `tests/`
**Current source LOC:** 744 (excl. `__init__.py`)

**🔔 Version bump detected: `0.1.2` → `0.1.3`** — per `wegofwd-llm-critique.md` §8, every version bump triggers a full re-critique (re-run sections 1–6, refresh the Snapshot table).

## Commits since baseline

```
2847a1a Merge pull request #1 from wegofwd2020-hub/fix/typed-anthropic-errors
593f130 fix(anthropic): map SDK exceptions to typed seam errors → v0.1.3
```

## Files changed (diffstat)

```
 pyproject.toml                  |  2 +-
 tests/test_anthropic_native.py  | 64 +++++++++++++++++++++++++++++++++++++++--
 wegofwd_llm/__init__.py         |  2 +-
 wegofwd_llm/anthropic_native.py | 49 ++++++++++++++++++++++++++++---
 4 files changed, 109 insertions(+), 8 deletions(-)
```

## What to do with this report

- **If it's a version bump or touches `contract.py` / `registry.py` / `errors.py`:** trigger a full re-critique — re-run `wegofwd-llm-critique.md` §1–§7 against the new HEAD. Update the Snapshot table.
- **If it only touches `tests/` or `pyproject.toml` cosmetic fields:** update test/LOC numbers in the critique's Snapshot table only; no §7 re-rank needed.
- **If the change is large enough that the §7 priority actions move:** also refresh the README `### wegofwd-llm (shared LLM seam)` Quick Summary block.
- **If a consumer of wegofwd-llm (StudyBuddy_OnDemand / SelfLearner / Kathai Chithiram) needs to bump its pin to ride this change:** add a note to the consumer's next critique-refresh delta noting which behaviour change is now exposed.

Merging this PR advances `wegofwd-llm-last-reviewed.txt` to `2847a1abb311446bb433996e76d2bcbd3d59be5f` — the next weekly watch will measure from this commit forward.

---

*Generated automatically by `wegofwd-llm/.github/workflows/watch.yml`. The critique itself is human/Claude-authored; this report is just the change-detection prompt.*
