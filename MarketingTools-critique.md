# MarketingTools — Code Review & Critique

**Reviewed:** 2026-06-09 (v1.0 — first review, measured on disk at branch `main` @ `76addee`)
**Repo:** `MarketingTools` (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/MarketingTools`)
**Reviewer:** Claude (Anthropic)
**Scope:** The whole toolkit as it stands on disk — `generate.py` (copy generator), `decks/` (python-pptx deck builders), `assets/` (the `products.yaml` source-of-truth + brand rules), `campaigns/` (CRM-lite CSV), `templates/`, `landing/` (stub). The `.venv-decks/` virtualenv is **excluded** from all measurements (it is a dependency cache, not project source).
**Rating key:** 🟢 Strong · 🟡 Gap / Risk · 🔴 Critical Issue

---

## What This Is

MarketingTools is a **small, single-author Python marketing toolkit** that markets a product portfolio (StudyBuddy OnDemand, Mentible, Pramana, home-school, special-needs video) from **one source of truth** (`assets/products.yaml`). Its thesis mirrors the products it markets: the same "scoped-retrieval" pattern, with the scope vector swapped from `(topic × grade × …)` to `(product × audience × channel × framing)`. Concretely it does three things today: (1) `generate.py` builds a scoped prompt from the asset library + brand rules and asks Claude for channel-ready copy; (2) `decks/` deterministically builds python-pptx pitch decks (three Mentible decks + one Pramana deck) over a shared brand-theme engine; (3) `campaigns/campaigns.csv` is a hand-maintained outreach log. Landing-page generation is an explicit, honest stub.

### Measured on disk (`76addee`, all `wc -l` / `git ls-files` / `find`, venv excluded)

| Metric | Value |
|---|---|
| Commits (total) | **4** (first 2026-06-01, last 2026-06-09 — ~8 days) |
| Git-tracked files (excl. venv) | **15** |
| Python source LOC | **1,790** (`generate.py` 173 · `decks/theme.py` 437 · `decks/build_decks.py` 886 · `decks/build_pramana.py` 294) |
| Data + docs LOC (yaml/md/csv) | **484** (`products.yaml` 130, six READMEs/templates/brand, one CSV) |
| **Total project source** | **~2,274 LOC** across **22 non-venv files** |
| Test files / test functions | **0 / 0** — no `test_*.py`, no `pytest`/`unittest`, no `tests/` dir |
| Runtime deps declared (`requirements.txt`) | **2** (`anthropic>=0.40.0`, `PyYAML>=6.0`) |
| Committed binaries | logo PNGs only (`decks/assets/*.png`); generated decks (`decks/out/*`) correctly **gitignored** |

This is a genuinely small tool. The findings below are real but modest, and the doc is sized to match — no padding.

---

## Executive Summary

For its size, MarketingTools is **clean, well-documented, and architecturally coherent**. `generate.py` is a disciplined thin CLI: it loads the YAML library + brand rules, builds a scoped prompt, and only then touches the network — with a `--dry-run` that lets you inspect the prompt with no API key and no spend, and a `--list` that needs neither. The single-source-of-truth principle (`products.yaml`) is stated, justified, and actually honored across the generator, templates, and the deck builders. The deck engine (`theme.py`) is a tidy multi-brand layout library that already serves two distinct visual identities (Mentible, Pramana) from one codebase via a `set_brand()` switch.

The honest gaps are exactly what you'd expect of an 8-day, 4-commit personal toolkit, and none are architectural mistakes:

1. **No tests at all** (0 of everything). The prompt-assembly logic in `build_prompt()` — framing-resolution heuristics, optional-field fallbacks, the `--list`/missing-arg validation — is pure, fast, and trivially unit-testable, yet untested.
2. **The dependency manifest is split and incomplete.** `requirements.txt` declares only `anthropic` + `PyYAML`. The deck builders need `python-pptx` + `Pillow`, which appear **only** as a copy-paste line inside `decks/README.md`. A fresh `pip install -r requirements.txt` cannot run `decks/build_decks.py`.
3. **Secrets handling is correct-but-shallow.** The Anthropic key is read from `ANTHROPIC_API_KEY` (never committed, never written to disk), `.env`/`*.key` are gitignored — good. But there is no `.env.example`, no key-format validation, and the email `wegofwd2020@gmail.com` is hardcoded into deck content.

None of these are hard to close; most are an hour of work.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟢 Strong | Clean separation: `products.yaml` source-of-truth → `generate.py` thin CLI → stdout; deck engine is a multi-brand layout library (`set_brand`). Data-driven — adding a product/channel is a YAML edit, no code change (verified: `build_prompt` reads `lib["products"]`/`lib["channels"]` generically). |
| Code Quality | 🟢 Strong | `from __future__ import annotations` + type hints throughout; no hardcoded absolute paths (`Path(__file__).resolve().parent`); clear docstrings. One dead import (`qn` in `theme.py:21`, never used). |
| Test Coverage | 🔴 Critical (for the area) | **Zero tests.** `build_prompt`/framing-resolution/arg-validation are pure and easily testable but uncovered. Deck builders are run-once scripts with no smoke test. |
| Documentation | 🟢 Strong | Six READMEs/notes for ~2.3k LOC — unusually thorough at this scale; root `README.md` explains the thesis, quick-start, and "adding a product/channel"; `landing/` honestly labels itself a stub. |
| Security | 🟡 Gap | Key from env only (correct); `.env`/`*.key` gitignored; no real keys committed (scanned). Gaps: no `.env.example`, no key validation, hardcoded contact email in deck content. |
| Scalability / Reproducibility | 🟡 Gap | **`requirements.txt` is incomplete** — `python-pptx`/`Pillow` (deck deps) live only in `decks/README.md`; the `.venv-decks` is not pinned/locked. A clean clone can run `generate.py` but not the decks. |

**Top 3 actions:** (1) Add `python-pptx` + `Pillow` to `requirements.txt` (or a `requirements-decks.txt`) so a clean clone can build decks. (2) Add a handful of `pytest` unit tests for `build_prompt` (framing resolution, missing-field fallbacks) and a deck smoke test (`build_*` writes a non-empty `.pptx`). (3) Ship a `.env.example` documenting `ANTHROPIC_API_KEY`, and parameterize the hardcoded contact email.

---

## 1. Architecture — 🟢 Strong

### Strengths

- **One source of truth, actually enforced.** `assets/products.yaml` is the single product/channel/framing registry. `generate.py:37-39` (`load_library`) reads it; `build_prompt` (`generate.py:50-104`) pulls every product field (`name`, `one_liner`, `proof_points`, `framings`, `demo_url`/`site_url`) from it; the deck builders cite it as their content source; `templates/whatsapp_demo_invite.md` and `landing/README.md` both reference it as the place a tagline edit propagates from. The README's claim ("one edit should propagate") is borne out in the code.
- **Truly data-driven extension.** Adding a product or channel is a YAML edit with **no code change** — confirmed: `build_prompt` indexes `lib["products"][product_key]` and `lib["channels"][channel_key]` generically and serializes the chosen framing with `yaml.safe_dump`. The README's "Adding a product or channel" section matches the implementation.
- **The generator is a genuinely thin CLI.** `generate.py` does load → build prompt → (optionally) call. The model is a pinned constant (`DEFAULT_MODEL = "claude-sonnet-4-6"`, `generate.py:34`) overridable by `--model`, and the `anthropic` SDK is imported *lazily* inside `main()` (`generate.py:156`) so `--list` and `--dry-run` work with the SDK absent. That is the right dependency-laziness for a tool whose IP is the scoping, not the model.
- **The deck engine is a small multi-brand framework, not a one-off.** `theme.py` defines a `Brand` dataclass and an active-brand global with `set_brand()` (`theme.py:59-89`); layouts (`title_slide`, `content_slide`, `columns_slide`, `flow_slide`, `table_slide`, `statement_slide`, `closing_slide`) read the active brand for color/wordmark/logo. `build_pramana.py` calls `T.set_brand(T.PRAMANA)` and the same layouts re-skin to indigo/gold with a text logotype fallback (`logo=None`). One engine, two identities — clean.

### Gaps & Risks

🟡 **The two halves have different, undeclared runtimes.** `generate.py` runs under the root `requirements.txt` (anthropic + PyYAML). `decks/` runs under a *separate* `.venv-decks` with `python-pptx` + `Pillow` documented only in `decks/README.md`. This is a reasonable split (the deck deps are heavy and unrelated to copy generation) but it is **undeclared in any manifest** — see §6.

🟡 **`build_decks.py` is large for a single file (886 LOC).** It is essentially three long, linear deck definitions (`build_investor`/`build_architect`/`build_author`), each ~250 lines of declarative slide calls. It is readable, but content and code are interleaved; a future refactor could lift the slide content into data (YAML, consistent with the project's own source-of-truth thesis) and keep the builder purely structural.

---

## 2. Code Quality — 🟢 Strong

### Strengths

- **Modern, typed, portable Python.** Every `.py` opens with `from __future__ import annotations`; functions carry type hints (`build_prompt(... framing: str | None, extra: str | None) -> str`). Paths are resolved relative to the file (`ROOT = Path(__file__).resolve().parent`, `generate.py:32`; same pattern in both deck builders) — **no hardcoded absolute paths anywhere** (verified by grep).
- **Good CLI ergonomics and error messages.** `argparse` with `choices` on `--framing`; explicit missing-arg handling that names the missing flags (`generate.py:132-135`); unknown-product/channel errors that point at `--list` (`generate.py:137-140`); clear exit codes (2 for "no key", with a hint to use `--dry-run`). `main()` returns an int and `raise SystemExit(main())` propagates it.
- **The theme helpers are well-factored.** `_rect`/`_text`/`_notes`/`_footer`/`_header` are small primitives the layouts compose; `_text` handles a mildly clever runs-of-runs format for mixed inline styling. Brand colors are named constants, not magic hex inline.

### Gaps & Risks

🟡 **One dead import.** `theme.py:21` imports `qn` (`from pptx.oxml.ns import qn`) but `qn` is never called anywhere in `decks/` (verified). Harmless, but it's the kind of thing a linter would flag — and there is no linter config in the repo.

🟡 **No linter / formatter config.** No `ruff`/`black`/`flake8` config, no `pyproject.toml`. The code *reads* as if it were linted (consistent style, no obvious smell beyond the dead import), but nothing enforces it. For a 2.3k-LOC personal toolkit that's defensible; a one-line `ruff` config would catch the dead import for free.

---

## 3. Test Coverage — 🔴 Critical (for this area)

**There are zero tests.** No `test_*.py` / `*_test.py`, no `conftest.py`, no `tests/` directory, and no `pytest`/`unittest` import anywhere in the tree (verified by `find` + `grep`). The rating is 🔴 for the *area* in absolute terms, tempered in the summary by the project's small scale and personal-tool nature — but the gap is real because the most logic-bearing code here is *exactly* the kind that is cheap to test:

- **`build_prompt` is pure and deterministic** — given a library dict + the five string args it returns a string with no I/O (it calls `load_brand()`, but that too is pure file reads). The framing-resolution branch (`generate.py:56-70`) has real logic worth pinning: explicit-flag-wins, `"both"`, the `prefer_tech` audience heuristic (`{"investors", "L&D_leads", "corporate_buyers"}`), and the consumer/all fallbacks. None of it is covered, so a regression (e.g. renaming an audience) would surface only in production copy.
- **Optional-field fallbacks are untested** — `product.get('demo_url') or product.get('site_url') or '(none — omit link)'` (`generate.py:83`) and the `proof_points`/`languages` empties have sensible defaults that no test guards.
- **The deck builders have no smoke test** — `build_investor()` etc. are run-once scripts; a 5-line test asserting each `build_*` returns a path to a non-empty file would catch a python-pptx API break or a broken brand switch before a pitch.

🔧 *Fix:* a single `test_generate.py` with ~8 cases (framing matrix, missing-field fallbacks, `--list` output, unknown-product error) plus a `test_decks.py` smoke test would move this area to 🟢 in an afternoon, against fully testable code.

---

## 4. Documentation — 🟢 Strong

### Strengths

- **Unusually thorough for the size.** Six docs for ~2.3k LOC: root `README.md` (the thesis, a what's-here status table, quick-start, "how the pieces fit" ASCII diagram, and "adding a product/channel"); `decks/README.md` (99 lines — venv setup, the `.pptx`→`.odp` `soffice` conversion, the Google-Slides upload path); `campaigns/README.md` (column semantics + a status ladder); `landing/README.md` (the deferred-stub plan); `templates/whatsapp_demo_invite.md` (a paste-ready, annotated template); and `assets/brand/studybuddy.md` (the brand rules that are literally injected into every generation).
- **The brand rules are documentation that is also runtime input.** `assets/brand/studybuddy.md` is `load_brand()`'d into every prompt (`generate.py:42-47`) — so the "the word *current* is load-bearing, never *today's*" rule isn't just a note, it's enforced into the model's context. Docs-as-config, done well.
- **Honest status labeling.** The README status table marks `landing/` as `🟡 stub`, and `landing/README.md` opens "**STUB (deferred)**" with the plan and a today-workaround. The `products.yaml` header explains the `home:` portfolio split and even records the `briefcase → pramana` rename and that it was propagated to `campaigns.csv`. This is candor, not aspiration.

### Gaps & Risks

🟡 **The deck-dependency instructions live only in prose.** `decks/README.md:33-34` tells you to `python3 -m venv ../.venv-decks` and `pip install python-pptx Pillow` — but this is documentation standing in for a manifest. Documentation drifts; a `requirements-decks.txt` would not. (See §6.)

🟡 **No top-level `LICENSE` or `CONTRIBUTING`.** Expected absences for a private internal tool, noted only for completeness.

---

## 5. Security — 🟡 Gap

### Strengths

- **The API key is environment-only and never persisted.** `generate.py:149` reads `os.environ.get("ANTHROPIC_API_KEY")`; if absent it errors with exit code 2 and a hint to use `--dry-run` (`generate.py:150-153`). The key is never written to disk, never logged, never an argparse argument (so it can't leak into shell history).
- **`.gitignore` covers the secret surfaces.** `.env`, `*.key`, and `__pycache__/`/`*.pyc` are ignored, and the generated-copy `out/` and `.venv-decks/` are ignored too. A repo scan for real keys (`sk-ant-...` patterns across `.py`/`.yaml`/`.md`/`.csv`) found **only the placeholder** `sk-ant-...` in usage examples — **no committed secrets**.
- **No real secrets in `.claude/settings.local.json`** — it only allow-lists a Google Drive MCP tool.

### Gaps & Risks

🟡 **No `.env.example`.** The only record that `ANTHROPIC_API_KEY` is the expected variable is the README quick-start and an inline error string. A committed `.env.example` (with a placeholder, not a key) is the conventional, discoverable way to declare it.

🟡 **No key-format validation.** `generate.py` passes whatever is in the env straight to `anthropic.Anthropic(api_key=...)`. A typo'd/empty-after-prefix key fails late with an SDK error rather than a friendly "that doesn't look like an `sk-ant-` key." Minor, but a one-line check improves the failure mode.

🟡 **Hardcoded contact email in deck content.** `wegofwd2020@gmail.com` is baked into closing slides across `build_decks.py` and `build_pramana.py`. Not a *secret*, but it's PII-adjacent boilerplate that belongs in `products.yaml`/a config constant so it lives in one place (consistent with the project's own source-of-truth principle).

---

## 6. Scalability / Reproducibility — 🟡 Gap

### Strengths

- **Generated artifacts are not committed.** `out/` (generated copy) and `decks/out/*.pptx`/`*.odp` are gitignored; only the small logo PNGs (`decks/assets/*.png`) are tracked. The repo stays source-only — correct hygiene.
- **The generator scales trivially.** It's a stateless per-invocation CLI; "scale" here means "add rows to a YAML file," which is O(edit). There is no server, no DB, no concurrency to reason about — appropriate for the job.

### Gaps & Risks

🔴→🟡 **`requirements.txt` is incomplete — the headline reproducibility gap.** It declares `anthropic>=0.40.0` and `PyYAML>=6.0` only. The deck builders import `pptx` (python-pptx) and the README's deck-setup also installs `Pillow` — **neither is in any manifest**; they exist only as a prose line in `decks/README.md:34`. Consequence: a clean clone that runs `pip install -r requirements.txt && python decks/build_decks.py` fails with `ModuleNotFoundError: No module named 'pptx'`. (Rated 🟡 overall because `generate.py` *is* fully covered by the manifest; the gap is isolated to the deck half.)

🟡 **The `.venv-decks` is unpinned.** Even following the README, `pip install python-pptx Pillow` resolves to whatever versions are current — no lockfile, no version pins for the deck deps, so a future python-pptx API change could silently break the builders. A `requirements-decks.txt` with pinned versions closes both this and the gap above.

🟡 **`soffice`/LibreOffice is an undeclared external tool dependency.** `build_pramana.py`'s `.odp` output path and `decks/README.md:45` require `soffice --headless` to be installed on the machine. Documented, but it's a system dependency outside any Python manifest — worth a one-line "Prerequisites" note at the top of the deck README.

---

## Priority Actions (Ordered)

| Priority | Action | Area |
|---|---|---|
| P1 | Add `python-pptx` + `Pillow` (pinned) to a `requirements-decks.txt` (or the root manifest) so a clean clone can build decks — the one reproducibility break | Reproducibility |
| P1 | Add `pytest` unit tests for `build_prompt` (framing matrix, optional-field fallbacks, `--list`, unknown-product error) + a deck smoke test | Test Coverage |
| P2 | Ship a `.env.example` declaring `ANTHROPIC_API_KEY`; add a light key-format check before the SDK call | Security |
| P2 | Move the hardcoded contact email into `products.yaml`/a config constant (one source of truth) | Security / Architecture |
| P3 | Remove the dead `qn` import in `theme.py:21`; add a minimal `ruff` config | Code Quality |
| P3 | Add a "Prerequisites: LibreOffice (`soffice`)" line to `decks/README.md` for the `.odp` path | Documentation |
| P3 | (Optional) Lift `build_decks.py` slide *content* into data, keeping the builder structural — consistent with the project's own source-of-truth thesis | Architecture |

---

*This critique is a point-in-time review measured against the code on disk at `76addee` (branch `main`, 2026-06-09), the 4-commit history, and the six in-repo docs. All numbers are from `wc -l`, `git ls-files`, `find`, and `grep` with the `.venv-decks/` virtualenv excluded. No tests were run because there are none to run. The toolkit is small and personal; the findings are sized to match — real, but modest, and nearly all an hour or less to close.*
