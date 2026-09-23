# OpenCode Agents & Modes

OpenCode lets you switch agents mid-session. Each agent has a different system
prompt, tool set, and output contract. Pick the one that matches your current job.

---

## Build (default)

Full access — read, write, shell. No approval gate.

**Use for:** general coding, implementing features, multi-file changes, running tests.

---

## Plan

Read and explore freely. Proposes writes before executing — waits for approval.

**Use for:** reviewing approach before a big change. Avoid for pure analysis tasks
(smaller models misread the gate as "do nothing").

---

## Cavecrew-Builder

Surgical editor. 1–2 files max. Hard refuses 3+ file scope. No new abstractions,
no drive-by refactors. Returns a diff receipt.

**Use for:** targeted fix, single-function rewrite, rename, comment removal.

**Refuses:** 3+ files → splits into subtasks. Ambiguous spec → asks one question.

---

## Cavecrew-Investigator

Read-only code locator. Returns `file:line` table. Never edits, never proposes fixes.
Output is caveman-compressed (~60% fewer tokens than vanilla exploration).

**Use for:** "where is X defined", "what calls Y", "map this directory".

**Output format:**
```
Defs:
  src/foo.py:42 — `MyClass` — base state machine
Callers:
  src/runner.py:18,55
2 defs, 2 callers.
```

---

## Cavecrew-Reviewer

Diff/file auditor. One finding per line, severity-tagged. No praise, no scope creep.

**Use for:** PR review, "audit this file", pre-commit check.

**Severity tiers:**

| Emoji | Tier | Meaning |
|-------|------|---------|
| 🔴 | bug | Wrong output, crash, security hole, data loss |
| 🟡 | risk | Edge case, race, leak, perf cliff, missing guard |
| 🔵 | nit | Style/naming — only if thorough review requested |
| ❓ | question | Need author intent before judging |

**Output format:**
```
path/to/file.py:42: 🔴 bug: problem. fix.
path/to/file.py:88: 🟡 risk: problem. fix.
totals: 1🔴 1🟡
```

---

## Recommended workflow for a new feature

1. **Cavecrew-Investigator** — map relevant files, symbols, callers
2. **Plan** — design approach, get approval
3. **Build** — implement
4. **Cavecrew-Reviewer** — audit diff before commit
