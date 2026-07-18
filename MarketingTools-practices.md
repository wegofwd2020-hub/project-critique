# MarketingTools — Good Practices, Bad Practices & How to Improve

**Document type:** Engineering practices analysis
**Scope:** The copy generator (`generate.py`, Python/argparse/PyYAML/anthropic), the deck engine (`decks/`, python-pptx), the asset library + brand rules (`assets/`), the outreach log (`campaigns/`), and the in-repo docs
**Reviewed:** 2026-06-09 (v1.0 — first review, measured on disk at branch `main` @ `76addee`)
**Repo:** `MarketingTools` (`/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/MarketingTools`)
**Author:** Claude (Anthropic)
**Related:** [MarketingTools-critique.md](MarketingTools-critique.md) · [MarketingTools-development-pattern.md](MarketingTools-development-pattern.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice · 🔧 How to improve

> A catalogue of concrete practices observed in the MarketingTools codebase, with fixes. The through-line: **the data-design and documentation practices are strong for the scale; the gaps are all engineering-hygiene** — no tests, a split/incomplete dependency manifest, and a couple of small one-source-of-truth violations (a hardcoded email, the deck-deps living in prose). None are architectural mistakes; nearly all are an hour or less to close.

---

## ✅ Good Practices

### ✅ One source of truth for marketing facts — and it's actually honored

`assets/products.yaml` is the single registry of products, taglines, links, proof points, audiences, and framings. The generator reads every product field from it (`generate.py:80-89`), templates reference it, and the deck builders cite it as their content source. The README forbids the anti-pattern explicitly ("Never hardcode a tagline outside `products.yaml`") and the YAML header forbids the inverse ("Don't generate into it"). The principle is stated *and* enforced in code — a tagline edit really does propagate.

🔧 *Reusable takeaway:* a source-of-truth claim is only real if the code reads it generically. Here `build_prompt` indexes `lib["products"][key]` rather than special-casing any product, so the registry can't quietly rot into "the file we used to read from."

### ✅ Make the no-API-call path first-class (and free)

`generate.py` exposes `--list` (products/channels, no SDK, no key) and `--dry-run` (print the exact prompt, no SDK, no key), and imports the `anthropic` SDK *lazily inside `main()`* so both work even if the SDK isn't installed. For a tool whose output is prompts, making the prompt inspectable for free — before any spend — is the right default.

🔧 *Takeaway:* any tool that calls a paid API should make "show me exactly what you'd send" reachable without a key or a charge. It's the cheapest correctness and cost-control affordance there is.

### ✅ Secrets from the environment, never on disk, never in argv

The Anthropic key is read only from `os.environ.get("ANTHROPIC_API_KEY")` (`generate.py:149`), never written to a file, never logged, and never an argparse argument (so it can't leak into shell history). `.env` and `*.key` are gitignored. A repo-wide scan found **no committed secrets** — only the placeholder `sk-ant-...` in usage examples.

### ✅ Don't commit generated artifacts

`.gitignore` excludes the generated-copy `out/`, the generated decks (`decks/out/*.pptx`/`*.odp`), the `.venv-decks/` virtualenv, and `__pycache__/`/`*.pyc`. Only source — including the small brand logo PNGs — is tracked. The repo stays clean and source-only (verified: `git ls-files decks/` shows only the two logo PNGs, no built decks).

### ✅ Portable paths — no hardcoded absolutes

Every entry point resolves its paths relative to the file (`ROOT = Path(__file__).resolve().parent` in `generate.py`; the same `Path(__file__).resolve().parent / "out"` in both deck builders). A grep for `/home/`, `/Users/`, and Windows drive paths in the Python source finds **none**. The toolkit runs from any clone location.

### ✅ Docs-as-runtime-config: brand rules injected into every generation

`assets/brand/studybuddy.md` isn't just documentation — `load_brand()` concatenates every `brand/*.md` into the prompt (`generate.py:42-47`), so the "the word *current* is load-bearing, never *today's*" rule is enforced into the model's context on every call, with a brand-rule violation framed as "a defect, not a style preference." The doc and the runtime constraint are the same artifact.

### ✅ A small framework generalized exactly as far as it needed to go

`decks/theme.py` supports two brands (Mentible, Pramana) via a `Brand` dataclass + `set_brand()`, with a `logo: Path | None` fallback so Pramana (no logo asset) renders a text wordmark instead. The generalization is *minimal and real* — it covers the exact variation the second brand required (color + logo-or-wordmark), not a speculative theming system.

### ✅ Documentation proportionate-and-then-some, including honest status

Six docs for ~2.3k LOC, each earning its place: the root README's thesis + quick-start + "adding a product/channel," the deck setup/conversion runbook, the CSV column semantics + status ladder, and the `landing/` stub that ships its own plan and interim workaround. Status is labeled honestly (`landing/` = `🟡 stub`; the YAML header records the `briefcase → pramana` rename).

---

## ⚠️ Bad Practices (and 🔧 fixes)

### ⚠️ Zero tests — on code that is trivially testable

There are no tests of any kind (no `test_*.py`, no `pytest`/`unittest`, no `tests/`). The logic-bearing core — `build_prompt`'s framing-resolution heuristic (`generate.py:56-70`), the optional-field fallbacks (`generate.py:83`), and the `--list`/missing-arg/unknown-product validation — is **pure and deterministic** and would take an afternoon to cover.

🔧 Add `test_generate.py`: assert the framing matrix (explicit flag wins; `"both"`; the `prefer_tech` audience set; the consumer/all fallbacks), the `demo_url or site_url or '(none)'` fallback, the `--list` output, and the unknown-product error. Add `test_decks.py`: a smoke test that each `build_*()` returns a path to a non-empty `.pptx` (catches a python-pptx API break or a broken brand switch before a real pitch).

### ⚠️ The dependency manifest is split and incomplete

`requirements.txt` declares only `anthropic>=0.40.0` + `PyYAML>=6.0` — the generator's deps. The deck builders import `pptx` and the README installs `Pillow`, but **neither is in any manifest**; they appear only as a prose line in `decks/README.md:34`. A clean `pip install -r requirements.txt && python decks/build_decks.py` fails with `ModuleNotFoundError: No module named 'pptx'`.

🔧 Add a `requirements-decks.txt` with pinned `python-pptx` + `Pillow` (and note `soffice`/LibreOffice as a system prerequisite for the `.odp` path). A manifest that doesn't reproduce the project is worse than none — it implies completeness it doesn't have.

### ⚠️ Hardcoded contact email — a one-source-of-truth violation by the project's own rule

`wegofwd2020@gmail.com` is baked into closing slides across `build_decks.py` and `build_pramana.py`. The project's own principle is "never hardcode a fact outside `products.yaml`," and a contact email is exactly such a fact.

🔧 Put the contact email (and any other shared boilerplate like the confidential footer) in `products.yaml` or a single `theme` constant, and have the builders read it — the same propagation guarantee the taglines already get.

### ⚠️ No `.env.example` and no key-format validation

The only record that `ANTHROPIC_API_KEY` is the expected variable is the README and an inline error string; the key is passed straight to the SDK with no shape check, so a typo'd/empty key fails late with an opaque SDK error.

🔧 Commit a `.env.example` (placeholder, not a key), and add a one-line `if not api_key.startswith("sk-ant-"): ap.error(...)` guard for a friendlier early failure.

### ⚠️ A dead import and no linter to catch it

`theme.py:21` imports `qn` (`from pptx.oxml.ns import qn`), which is never used. There is no `ruff`/`flake8`/`pyproject.toml` config, so nothing flags it.

🔧 Remove the import; add a minimal `ruff` config (`[tool.ruff]` with a handful of rules). For a 2.3k-LOC tool that's the right weight — it catches dead imports and unused vars for free without ceremony.

### ⚠️ `build_decks.py` interleaves content and code at 886 LOC

The three deck definitions are long, linear sequences of slide calls with the *copy* embedded inline. It's readable, but it means a content edit is a code edit, and the file is the largest in the repo by far.

🔧 (Optional, lower priority.) Lift the slide content into data (YAML — consistent with the project's source-of-truth thesis) and keep `build_decks.py` as the structural builder. Not urgent for an 8-day tool, but it's the natural next refactor if the decks grow.

---

## 🔧 Testing practices — currently absent

| Practice | State | Fix |
|---|---|---|
| Unit tests for `build_prompt` (framing/fallbacks) | ⚠️ Absent | Pure function — ~8 cases, an afternoon |
| Arg-handling tests (`--list`, missing/unknown args) | ⚠️ Absent | `argparse` exits are easy to assert via `SystemExit` |
| Deck smoke test (`build_*` → non-empty `.pptx`) | ⚠️ Absent | Catches python-pptx breaks + brand-switch regressions |
| Linter / formatter gate | ⚠️ Absent | One `ruff` config; would already catch the dead `qn` import |
| CI | ⚠️ Absent | A single GitHub Action running `ruff` + `pytest` would lock all of the above |

---

## Practices Scorecard (v1.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│  MarketingTools — Practices Scorecard (v1.0, @ 76addee)              │
├──────────────────────────────────────┬───────────┬───────────────────┤
│  Practice area                        │  Rating   │  Note              │
├──────────────────────────────────────┼───────────┼───────────────────┤
│  Single source of truth (products.yaml)│  ✅ Strong │  enforced in code  │
│  No-API/dry-run path first-class      │  ✅ Strong │  --list / --dry-run│
│  Secrets from env, none committed     │  ✅ Strong │  scanned clean     │
│  Don't commit generated artifacts     │  ✅ Strong │  out/ gitignored   │
│  Portable paths (no absolutes)        │  ✅ Strong │  Path(__file__)    │
│  Docs-as-runtime brand rules          │  ✅ Strong │  load_brand()      │
│  Minimal-but-real framework (2 brands)│  ✅ Good   │  set_brand fallback│
│  Documentation coverage + honest status│  ✅ Good   │  6 docs / 2.3k LOC │
│  Dependency manifest completeness     │  ⚠️ Weak   │  pptx/Pillow only  │
│                                       │           │  in README prose   │
│  Test coverage                        │  ⚠️ Gap    │  zero tests        │
│  Linter / CI gate                     │  ⚠️ Gap    │  none              │
│  Secret-handling polish (.env.example)│  ⚠️ Minor  │  no example/validate│
│  One-source email (vs hardcoded)      │  ⚠️ Minor  │  email baked in    │
└──────────────────────────────────────┴───────────┴───────────────────┘
```

The shape is telling and consistent with the sibling projects at small scale: **everything about data design, secrets, and documentation is strong; every weak item is engineering hygiene** — tests, a complete manifest, a linter, and two small "put this fact in the one place" cleanups. None are architectural; all are cheap.

---

*Practices observed in the code on disk at `76addee` (branch `main`, 2026-06-09), the 4-commit history, and the six in-repo docs, with the `.venv-decks/` virtualenv excluded from all measurements. `pytest` and `ruff` were not run because the repo ships neither tests nor a lint config; the "zero tests" and "dead import" findings are from `find`/`grep` on disk. The toolkit is small and personal — the fixes are sized accordingly.*
