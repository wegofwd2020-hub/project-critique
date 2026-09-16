# LLM-in-the-Loop Automation Pipeline — Pattern Definition

**Document type:** Cross-project engineering pattern
**First used:** `wegofwd-arivu` corpus curation, September 2026
**Scope:** Any WeGoFwd project that needs automated data work with a subjective judgment step
**Doc updated:** 2026-09-16
**Related:** [kathai-chithiram-practices.md](kathai-chithiram-practices.md) · [claude-code-workflow-improvements.md](claude-code-workflow-improvements.md)

---

## What This Pattern Is

A **shell-orchestrated pipeline** where:

1. **The script does the deterministic work** — fetch, filter, gate, format. Pure logic, verifiable, reproducible.
2. **A local LLM (Ollama) handles the judgment step** — relevance ranking, curation, structured drafting. The one step that requires domain reasoning.
3. **You review before anything is committed** — the human gate catches LLM errors before they reach the codebase.

This is not an agent. The LLM does not drive the pipeline. It answers a single bounded question inside a pipeline the shell controls.

---

## The Three Layers

```
┌─────────────────────────────────────────────┐
│  SHELL SCRIPT (orchestrator)                │
│  - fetch data from APIs                     │
│  - enforce hard gates (licence, format)     │
│  - format candidates for LLM               │
│  - validate LLM output against ground truth │
│  - write structured output (JSON / Python)  │
└──────────────────┬──────────────────────────┘
                   │  bounded prompt
                   ▼
┌─────────────────────────────────────────────┐
│  OLLAMA (judgment layer)                    │
│  - answers one subjective question          │
│  - ranks, selects, or drafts               │
│  - output is validated by the shell         │
└──────────────────┬──────────────────────────┘
                   │  structured output
                   ▼
┌─────────────────────────────────────────────┐
│  HUMAN REVIEW GATE                          │
│  - reads the output file                    │
│  - makes the commit decision                │
│  - corrects obvious errors before patching  │
└─────────────────────────────────────────────┘
```

---

## The Critical Safety Property: Hallucination Guard

LLMs fabricate plausible-looking output. Every LLM output must be validated against the ground-truth set the script already holds.

**Rule:** Only accept LLM-selected items that were in the shell's admitted set. Anything else is silently dropped with a log line.

```bash
# Shell validates every LLM pick before accepting it
for pmcid in "${ollama_picks[@]}"; do
  valid=0
  for admitted in "${admitted_set[@]}"; do
    [[ "$admitted" == "$pmcid" ]] && valid=1 && break
  done
  if [[ $valid -eq 1 ]]; then
    SELECTED+=("$pmcid")
  else
    echo "  → hallucinated '${pmcid}' — dropped" >&2
  fi
done
```

Without this guard, a hallucinated ID silently enters the codebase. With it, the LLM can only *choose from* what the pipeline already verified.

---

## Existing Implementations in This Portfolio

### 1. `wegofwd-arivu/scripts/seed_pmc.sh` — corpus seed curation

- **Deterministic:** NCBI esearch → BioC licence gate (CC0/CC-BY only) → esummary titles
- **LLM judgment:** Ollama picks best 3 articles per condition for families of children with disabilities
- **Output:** Python tuple for `PMC_SEED_PMCIDS` in `sources/pmc.py`
- **Human gate:** review titles, drop bad picks, then `patch it`

### 2. `wegofwd-arivu/scripts/check_entitlements.sh` — entitlement validation

- **Deterministic:** load existing programs.toml, search corpus for evidence by condition
- **LLM judgment:** Ollama evaluates coverage gaps and drafts TOML entries from verbatim corpus quotes
- **Output:** gap report + candidate TOML for human to review before adding to `programs.toml`
- **Human gate:** manually verify every quote is a verbatim substring before committing

---

## When to Use This Pattern

✅ **Use when:**
- Task requires fetching and filtering a large candidate set (APIs, files, DB)
- One step in the pipeline needs subjective domain judgment (relevance, quality, fit)
- Output can be reviewed by a human before it affects the codebase
- A local Ollama model has enough domain knowledge for the judgment step
- You want a repeatable, auditable pipeline you can re-run as data grows

❌ **Do not use when:**
- The judgment step requires zero errors (medical dosing, legal eligibility decisions)
- Output goes directly to production without human review
- The LLM's output cannot be validated against a known-good set
- The pipeline needs to run unattended in CI (LLM outputs are non-deterministic)

---

## How to Adopt in a New Project

**Step 1 — Identify the judgment step.**
What part of your automation requires a human-like decision? Ranking? Drafting? Classification? That is the only step the LLM handles.

**Step 2 — Build the deterministic pipeline first.**
Fetch, filter, and format candidates entirely in shell/Python *before* involving Ollama. The LLM should receive a clean, bounded input — not raw API responses.

**Step 3 — Write a tight prompt.**
Give the LLM: context (who this is for), the candidate list, a clear selection criterion, and a strict output format (one item per line, or JSON). Vague prompts produce vague output.

**Step 4 — Add the hallucination guard.**
Before using any LLM output, check every item against the pipeline's ground-truth set. Drop anything not in the set. Log the drop.

**Step 5 — Write to a review file, not directly to source.**
Output to `/tmp/project_seed.py` or similar. The human reads, edits if needed, then pastes or triggers the patch. Never let the script write to `src/` automatically.

**Step 6 — Name env vars for the knobs.**
`OLLAMA_MODEL`, `RETMAX`, `PICK_PER`, `SLEEP_S` — callers override without editing the script.

---

## Quality Signals for the Judgment Step

Watch for these in Ollama's output — they indicate the model went off-track:

| Signal | What it means |
|---|---|
| Picked an ID not in the candidate list | Hallucination — the guard catches this |
| Picked items from a different category | Prompt context was too vague |
| All picks are identical across conditions | Model defaulted to generic output |
| Output is prose, not the requested format | Prompt format instruction too weak |
| Skipped an entry in the TOML draft | Model silently omitted required fields |

When signals fire, tighten the prompt or increase the candidate pool — not the trust in the output.

---

## Model Selection

- **Default:** whatever is installed (`ollama list`) — `llama3.2`, `mistral`, etc.
- **Better for structured output:** `mistral`, `phi3`, `gemma2` tend to follow format instructions more reliably than chat-optimised models
- **For long candidate lists (>20 items):** use a model with a larger context window (`llama3.1:8b` minimum)
- **Never route real child/family data through Ollama** — Ollama is local but the WeGoFwd no-training/ZDR policy applies to all LLM invocations on sensitive data. Corpus curation (public scientific literature) is fine.
