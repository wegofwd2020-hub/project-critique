# Kathai Chithiram — Good Practices, Bad Practices & How to Improve

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/kathai-chithiram` |
| Branch | `main` |
| Git commit | `e19ca0d` (as of 2026-09-13) |
| Product version | 0.1.0 |
| Doc updated | 2026-09-13 |
| Last deployed | TODO — set last deployment date-time (not in git) |
<!-- doc-meta:end -->

**Reviewed:** 2026-09-13 (v1.0 — first review, against `main` at `e19ca0d`)
**Related:** [kathai-chithiram-critique.md](kathai-chithiram-critique.md) · [kathai-chithiram-development-pattern.md](kathai-chithiram-development-pattern.md)
**Rating key:** ✅ Good · ⚠️ Bad / Risk · 🔧 How to improve

---

## 1. Architecture Practices

### ✅ Good — One narrow LLM seam; everything that can be deterministic is
The only model call is `AnthropicProvider.complete`, reached solely through `run_generation`. Validation, rendering, safety guards, offline generation and the progress engine are pure. The model's blast radius is a dict of strings a deterministic validator gates.

### ✅ Good — The scene-script is a real, versioned contract
v1/v2 JSON schemas; v2 closes the vocabulary. Three producers (LLM, `--offline`, `author` template) all target the same contract, and validation runs twice (after generation, again in the renderer).

### ⚠️ Bad — `cli.py` is a 1,818-line god-file
Eighteen subcommands in one module (`storage/store.py` is a second outlier at 1,102). Everything else is ≤440 lines.
🔧 Split `cli.py` into per-command modules behind the existing dispatch table; the commands already delegate to services, so this is mechanical.

### ⚠️ Bad — "Two renderers" but only one is wired
Only `MatplotlibStickFigureRenderer` is CLI-reachable; the Blender v2 renderer runs only inside `blender --background`.
🔧 Either wire a `--renderer blender` path (shelling out to Blender) or state clearly in the README that Blender is an offline/experimental renderer, not a product path.

## 2. Safety & Child-Protection Practices

### ✅ Good — Three independent safety layers, none trusted alone
Generation-prompt rules as data (`system_prompt.py`), deterministic scene-script validation (flags reject the whole script; caption must equal narration; `experiential` intent rejected), and render-time guards (8–30 fps, ≤3 Hz flash, strobe-burst, audio caps). Unsafe output is never promoted draft→final.

### ✅ Good — The human review gate cannot be bypassed
`kc review` requires an identified reviewer and a guard-passing draft before approval; delivery is flagged only on approval; intake refuses to start without all three consents.

### ✅ Good — Safety errors surface, they don't get swallowed
A provider safety refusal is raised as a domain error; validation error messages are scrubbed of raw story text before they can be logged.

### ⚠️ Bad — Content *appropriateness* has no deterministic check
The strongest rules (no frightening imagery, transform distress, refuse risk-of-harm) live only in the LLM prompt; the deterministic layer checks structure/flags/flashing/audio, not narrative meaning.
🔧 This is ADR-001-intentional (human review is the backstop), but a lightweight deterministic lexical guard (banned-topic / medical-claim patterns) would add a real second net cheaply. At minimum, document that the human gate is the *only* meaning-level check.

### ⚠️ Bad — The risk-of-harm escalation path is unbuilt
ADR-009 D7 names it as a precondition for the wider product; it does not exist yet.
🔧 Build the escalation path (route flagged content to a human channel) before Surface 2 work starts, as the ADRs already require.

## 3. Privacy & Security Practices

### ✅ Good — Pseudonymize before egress, hard-stop on leaks
Child name → token before generation, reinserted only at render; `IdentifierLeakError` aborts dispatch if any residual identifier survives minimization; audit records store lengths, never text.

### ✅ Good — ZDR-or-refuse, failing closed
`build_zdr_provider` raises `ProviderConfigError` if `ANTHROPIC_ZDR_API_KEY` is absent rather than falling back to an ambient key; a provider lacking no-training/zero-retention is refused.

### ✅ Good — Encryption at rest, deny-by-default access, verifiable deletion
AES-256-GCM keyed by `KC_STORAGE_KEY`; `GuardedStore` deny-by-default access (ADR-004); retention sweep with verifiable hard-delete + crypto-shred; `.env`/`*.key`/`stories/` gitignored and untracked.

### ✅ Good — Supply chain pinned deliberately
`wegofwd-arivu` to an immutable commit SHA, `wegofwd-video` to a tag, with a comment stating the pinning policy.

### ⚠️ Bad — No SAST on special-category children's data
No bandit/semgrep/pip-audit — not in deps, not configured, not run.
🔧 Add `bandit -r src` and `pip-audit` to the (to-be-created) CI; both are near-zero-effort and directly proportionate to the data sensitivity.

## 4. Code Quality Practices

### ✅ Good — mypy `--strict` passes clean across 74 files
Effectively full annotation; third-party gaps handled via deliberate `ignore_missing_imports` overrides, not blanket loosening.

### ✅ Good — Zero inline debt markers
No `TODO`/`FIXME`/`HACK`/`XXX` in src or tests; debt lives in TICKETS/ADRs where it can be tracked and prioritised.

### ⚠️ Bad — The repo fails its own linter
`ruff check .` → `BLE001` (blind-except) at `generation/generator.py:120` — the exact rule the project added to `ruff` to enforce CLAUDE.md's "no blind except."
🔧 Fix the one `except Exception:` (catch the specific retrieval error, or re-raise) and — critically — put `ruff check` in CI so it can never regress silently again.

### ⚠️ Bad — No formatter, and the documented dev command is red
No black / `ruff format`; CLAUDE.md's `mypy .` fails on a test-path collision (green path is bare `mypy`).
🔧 Add `ruff format`; fix CLAUDE.md to document the command that actually passes.

## 5. Testing Practices

### ✅ Good — 735 tests, mirroring `src/` 1:1, all green (734/1 skip)
Every substantive module is exercised; the layout makes coverage gaps visible by structure.

### ✅ Good — External deps stubbed honestly
matplotlib/PIL/imageio via `pytest.importorskip`; Blender via a *gated-error* assertion rather than invoking `bpy`; the LLM via hand-rolled `FakeClient`/`FakeStream`; arivu grounding via `skipif`. Tests do not pretend to exercise what they can't run.

### ⚠️ Bad — No property-based testing and no coverage number
`hypothesis` is in zero test files despite the validator and safety guards (numeric bands, flash-rate) being ideal fuzz targets; coverage is asserted structurally, never measured.
🔧 Add `hypothesis` properties for the scene-script validator and `rendering/safety.py`; add `pytest-cov` and publish a number, even if only to find untested branches inside well-named files.

### ⚠️ Bad — The live LLM path is only tested with fakes
The Anthropic adapter assumes advanced API params (`thinking: adaptive`, `output_config.effort`, `format: json_schema`); nothing verifies the real SDK/API supports them.
🔧 Add one opt-in, key-gated smoke test (skipped in normal runs) that exercises a real generation against the ZDR credential, so an API drift is caught before a demo.

## 6. Process & Documentation Practices

### ✅ Good — Spec-first, SDD, reviewed-PR workflow, on disk
`docs: spec` → `docs: implementation plan` → feature commits → reviewed merge; `.superpowers/sdd/` holds the progress ledger and per-branch review diffs. The discipline is real, not claimed.

### ✅ Good — ADR status vocabulary is exemplary
*Proposed* vs *Accepted* vs "switched on," a "waiting on a person" blocker table, and the honest note that 006–012 are unbuilt. Best-in-portfolio at distinguishing intent from reality.

### ⚠️ Bad — Provenance and citations are labelled less carefully than status
The README's "shared `wegofwd-llm` package" is actually a local vendored module; ADR-026 is cited 12+ times but has no file in-repo.
🔧 Rename the local seam or drop the "shared package" language; add an ADR-026 pointer stub (as was done for ADRs 010/011 moved to `wegofwd-arivu`) so the citation resolves.

### ❌ The single highest-leverage fix — there is no CI at all
No `.github/`; nothing runs tests, mypy, ruff, or a SAST on merge. Every "good practice" above is self-discipline, and the live ruff failure is the proof that self-discipline drifts.
🔧 Add one GitHub Actions workflow: `pytest`, `mypy`, `ruff check`, `bandit -r src`, `pip-audit`. It converts the entire practices story from "claimed" to "enforced" in a single file.
