# Claude Code Workflow — Improvements & Implementation Guide

**Document type:** Workflow improvements for AI-assisted development
**Scope:** Claude Code CLI usage across StudyBuddy_OnDemand and Thittam
**Period:** April 2026
**Audience:** Solo developer using Claude Code as primary collaborator
**Rating key:** 🔥 High leverage · ⚙️ Medium · 📌 Nice-to-have

---

## Table of Contents

1. [Workflow Discipline](#1-workflow-discipline)
2. [Automation — Hooks & Slash Commands](#2-automation--hooks--slash-commands)
3. [Cadence & Measurement](#3-cadence--measurement)
4. [Risk Isolation](#4-risk-isolation)
5. [Living Artefacts](#5-living-artefacts)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## What You're Already Doing Well

Before the gaps, the foundation is strong:

- ✅ **Global coding standards** (`~/coding-standards/CODING_RULES.md`) loaded into every session via `~/.claude/CLAUDE.md`
- ✅ **Per-language conventions** (Go, Python) imported by reference
- ✅ **Per-project CLAUDE.md** files refreshed as the project evolves
- ✅ **ADRs** for architecture decisions (Thittam has 13)
- ✅ **Doc-drift CI** (Rule #16) catches stale documentation
- ✅ **11 standard architecture diagrams** (Rule #17) for any complex project
- ✅ **Three-tier secret classification** (T1 Vault / T2-3 env / T4 config)
- ✅ **Auto-memory system** for cross-session continuity
- ✅ **Periodic critique reviews** (StudyBuddy v1.1 → v1.2 → v1.3)
- ✅ **Doc separation** (code repo + docs repo)

The gaps below are workflow practices that would have made the build faster, safer, and more reproducible.

---

## 1. Workflow Discipline

### 🔥 1.1 Spec-First / Acceptance-First Prompts

**What it is.** Before "implement X," ask Claude to write the failing test, the API contract, or the acceptance criteria. Approve the spec, then implement.

**Why it matters.** Most of the v1.1 critique findings (synchronous Stripe in async router, JWKS cache with no TTL, `upsert_student` `account_status` bug) would have been caught at the spec stage rather than after implementation. A spec is a verification artefact — it doesn't disappear after the feature ships.

**How to implement.**

1. Adopt a standard prompt template:
   ```
   Before writing implementation, draft:
     1. The failing test (pytest/vitest/playwright as appropriate)
     2. The API contract (request/response schema, error cases)
     3. Acceptance criteria as a checklist

   Wait for my approval before implementing.
   ```
2. Save it as a snippet, or codify as a slash command (see §2.2).
3. For new endpoints in StudyBuddy, the spec must include: idempotency key handling, rate limit, RLS scope, observability fields. For Thittam services, the spec must include: which gRPC method, vertical config interaction, audit log entry.

**Example.** New endpoint `POST /api/v1/school/{id}/teachers/invite`:
- Failing test: `test_school_teacher_invite_creates_pending_record`, `test_school_teacher_invite_idempotent_on_duplicate_email`, `test_school_teacher_invite_rejects_non_super_admin`.
- Contract: `{email, role, school_id}` → `{invite_id, status: "pending", expires_at}`. Errors: 403 (RBAC), 409 (already invited), 429 (rate-limited).
- Acceptance: Invite expires after 7 days. Reuses `Idempotency-Key` header. Audit log row written. Email queued via Celery.

---

### 🔥 1.2 Plan Mode for Architectural Work

**What it is.** Use `/plan` (or the ExitPlanMode tool) for any change touching three or more files, or any change that crosses a service/module boundary.

**Why it matters.** Plan mode forces an explicit design step. Claude proposes the file-by-file diff before any code is written. This is the same discipline as a code review *before* the code exists.

**How to implement.**

1. Treat plan mode as mandatory for: new migrations, new endpoints, refactors touching ≥3 files, anything crossing a service boundary.
2. The output of plan mode should be saved as a temporary `.plan.md` file in the working directory if the plan is non-trivial — discard after merge.
3. For Thittam, plans involving the vertical plugin system should explicitly call out which YAML schema fields are touched.
4. For StudyBuddy, plans involving Stripe webhooks should explicitly call out which event types and which idempotency guarantees apply.

**Example trigger phrases that should force plan mode:**
- "Add a new service…"
- "Refactor X to support Y…"
- "Migrate from A to B…"
- "Add a new vertical for…"
- "Replace the current X implementation…"

---

### 🔥 1.3 Sub-Agent Fleet, Not Solo Conversation

**What it is.** Run specialized sub-agents (`Explore`, `Plan`, `code-reviewer`, `security-review`) in parallel for independent work, instead of using the main conversation thread for everything.

**Why it matters.** Sub-agents (a) protect your context window (you only see their summary), (b) run concurrently when independent, (c) bring fresh "outside-view" judgment. The two project critiques (this very document family) prove the value of an outside-view review — make it a regular practice, not an annual event.

**How to implement.**

1. Default rule: if a task requires reading more than ~3 files for context, delegate to `Explore`.
2. For any non-trivial PR, run `code-reviewer` and `security-review` sub-agents in parallel before merge.
3. For research questions ("how does X work in this codebase?"), always delegate to `Explore` rather than searching from the main thread.
4. For independent tasks (e.g., write tests + write docs + refactor naming), launch them as parallel sub-agent calls.

**Anti-pattern to avoid.** Asking the main conversation to "search the codebase for all usages of X, then refactor them" — this fills your context with raw search output. Delegate the search; act on the summary.

---

## 2. Automation — Hooks & Slash Commands

### 🔥 2.1 PreToolUse / PostToolUse Hooks

**What it is.** Hooks configured in `.claude/settings.json` that run shell commands automatically on tool events (e.g., after every `Edit`, after every `Write`, before `Bash`).

**Why it matters.** You currently enforce "run tests after edits" and "run lint before commit" via discipline + CI. Hooks make these unmissable — they fail fast, in the same conversation, and Claude sees the failure immediately.

**How to implement.**

1. Create `.claude/settings.json` in each project repo with hooks for:
   - **PostToolUse on Edit/Write:** run `ruff check --fix` (Python) or `eslint --fix` (TS) on the changed file.
   - **PostToolUse on Edit to migrations:** run `alembic check` to validate the migration graph.
   - **PreToolUse on Bash with `git push`:** run the full test suite and block on failure.
   - **Stop hook:** run `pytest -x` quickly on changed modules so failures surface before you read Claude's summary.
2. For Thittam, add a hook on edits to `*.proto` files that runs `buf generate` and stages the regenerated files.
3. For StudyBuddy, add a hook on edits to `backend/src/*/router.py` that runs `python scripts/export_openapi.py` and stages the result.

**Example `.claude/settings.json` snippet:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "filePathPattern": "**/*.py",
        "command": "ruff check --fix \"$CLAUDE_TOOL_FILE_PATH\""
      },
      {
        "matcher": "Edit|Write",
        "filePathPattern": "backend/alembic/versions/*.py",
        "command": "cd backend && alembic check"
      }
    ]
  }
}
```

**Reference.** Use the `update-config` skill to actually modify settings.json correctly — don't hand-edit.

---

### 🔥 2.2 Custom Slash Commands for Repeated Workflows

**What it is.** Project-scoped slash commands stored in `.claude/commands/*.md` that codify your repeated workflows.

**Why it matters.** You've done these patterns dozens of times (new migration, new endpoint, new ADR). Each time you re-explain the structure. A slash command captures the structure once and you invoke it.

**How to implement.**

Create `.claude/commands/` in each repo and add commands for the workflows you repeat. Each command is a markdown file with frontmatter.

**For StudyBuddy — suggested commands:**

| Command | Purpose |
|---|---|
| `/new-migration <name>` | Generate Alembic migration scaffold + matching downgrade test |
| `/new-endpoint <module>` | Spec-first endpoint flow: test → schema → router → service → audit |
| `/new-adr <title>` | New ADR with template, increments numbering, links from index |
| `/regen-openapi` | Run `scripts/export_openapi.py` + `npm run gen:types`; commit if drift |
| `/check-rls` | Verify RLS coverage on tenant-scoped tables; flag missing policies |
| `/review-pr` | Run `code-reviewer` + `security-review` sub-agents on current diff |

**For Thittam — suggested commands:**

| Command | Purpose |
|---|---|
| `/new-service <name>` | Scaffold the 6-file service layout (models/errors/repository/service/test/handler) |
| `/new-vertical <name>` | New vertical plugin: YAML config + status enum + icon set + sample seed |
| `/new-proto <service>` | Add proto, run `buf generate`, scaffold handler + test |
| `/new-adr <title>` | Same pattern as StudyBuddy |
| `/check-doc-drift` | Run `tools/check-doc-drift` against `thittam_docs` |
| `/audit-money` | Grep for `float64` near monetary fields; flag violations of Rule #1 |

**Example command file** (`.claude/commands/new-adr.md`):
```markdown
---
description: Create a new ADR with the project template
---

Create a new Architecture Decision Record:

1. List existing ADRs in docs/adr/ to determine the next number.
2. Create docs/adr/NNNN-<slug>.md with the standard template:
   - Status (Proposed / Accepted / Deprecated / Superseded)
   - Context (the forces at play, business + technical)
   - Decision (the choice and its rationale)
   - Consequences (positive, negative, neutral)
   - Alternatives Considered
3. Update docs/adr/index.md with the new entry.
4. Show me the draft before committing.

ADR title: $ARGUMENTS
```

---

### ⚙️ 2.3 Standing Quality Gates as Slash Commands

**What it is.** Commands that bundle multiple checks Claude should run before flagging work as done.

**Why it matters.** "Done" should mean "tests + lint + types + docs + drift checks all green," not "code compiled." Codify the gate.

**How to implement.**

Add `/done` and `/ship-ready` commands per project:

```markdown
---
description: Run the full quality gate before declaring work complete
---

Run these checks in parallel and report the result:

1. Backend: pytest tests/ + per-module coverage script + ruff + bandit
2. Web: npm test + npm run lint + npm run typecheck + npm run build (no emit)
3. API contract: scripts/export_openapi.py + npm run gen:types — fail if diff
4. Migrations: alembic check
5. Docs drift: any module-level docstring mentioning a renamed function?

Only declare "done" when all green. Otherwise list failures.
```

---

## 3. Cadence & Measurement

### 🔥 3.1 Scheduled Critique Cadence

**What it is.** Run the project critique sub-agent (the same pattern that produced this `studybuddy-critique.md` v1.1 → v1.2 → v1.3) on a recurring schedule, not just at milestones.

**Why it matters.** You ran v1.1 → v1.2 → v1.3 manually, weeks apart. Drift between reviews accumulates silently. A weekly or bi-weekly automated critique surfaces drift while it's still cheap to fix.

**How to implement.**

1. Use the `/loop` skill or the `schedule` skill to run a recurring critique.
2. The critique sub-agent prompt (template):
   ```
   Re-review <project> against the most recent critique document
   (path: project-critique/<project>-critique.md).

   Identify:
     - Items previously flagged that are now resolved
     - Items previously flagged that are still open
     - New issues introduced since the last critique

   Report changes only — do not repeat unchanged content.
   Output: a diff-style summary I can review in under 5 minutes.
   ```
3. Store the output as a dated file (`critique-YYYY-MM-DD.md`) so you have a trail.
4. Suggested cadence: **bi-weekly** during active development, **monthly** in steady state.

**Example schedule entry** (via `schedule` skill):
- Cron: `0 9 * * 1` (Mondays 9am)
- Task: Run critique sub-agent on StudyBuddy + Thittam in parallel; commit deltas to `project-critique/`.

---

### ⚙️ 3.2 Decision / Experiment Log

**What it is.** A `DECISIONS.md` (or `EXPERIMENTS.md`) file per project that captures what was tried and didn't work — alongside ADRs which capture only what shipped.

**Why it matters.** ADRs are biased — they document successes. The dead ends are forgotten and re-explored months later by a future you (or a future Claude session). Capturing failures saves the most expensive type of work: re-discovery.

**How to implement.**

1. Create `docs/DECISIONS.md` (or `EXPERIMENTS.md`) at the root of each repo.
2. Format: append-only, dated entries. Template:
   ```markdown
   ## 2026-04-15 — Tried: X | Outcome: Rejected

   **Context:** Why we considered this.
   **Approach:** What we tried.
   **Result:** Why it didn't work (be specific — error message, performance number, design conflict).
   **Alternative chosen:** Link to ADR or commit.
   ```
3. Add a slash command `/log-experiment` that prompts you for the four fields and appends to the file.
4. When Claude proposes a refactor, the first prompt should be: "Check `DECISIONS.md` — has this been tried before?"

**Example entries from your projects (reconstructed from critiques):**
- StudyBuddy: "Tried in-process slowapi for cross-worker rate limiting. Rejected: in-process state means 4 workers × 10 req/min = 40 req/min effective. Replaced with Redis INCR/EXPIRE dependency."
- Thittam: "Considered tenant-per-database for isolation. Rejected: 100+ tenants would mean 100+ Postgres clusters with separate backups. Chose tenant-per-schema with RLS instead."

---

### ⚙️ 3.3 Prompt Evals

**What it is.** A small suite of "given this codebase state, did Claude produce the right answer" tests. Re-run when upgrading models or rewriting CLAUDE.md.

**Why it matters.** When you change `~/coding-standards/CODING_RULES.md` or upgrade from Opus 4.6 to 4.7, you have no way to know if Claude's answers got better, worse, or just different. Evals give you a baseline.

**How to implement.**

1. Create `evals/` directory at the root of `~/coding-standards/`.
2. Each eval is a markdown file:
   ```markdown
   ## Eval: New Money Field

   **Prompt:** "Add a `total_revenue` field to the production model. It stores
   currency in USD with 2 decimal places."

   **Expected behaviours:**
     - Field type is `decimal.Decimal` (Go) or `Decimal` (Python), not float
     - DB column is NUMERIC(14,2)
     - JSON serialises as string
     - Reference to Rule #1 in the response

   **Acceptance:** All 4 behaviours present.
   ```
3. Re-run the eval set manually after any change to coding standards or model upgrade.
4. Suggested initial eval set (10 evals): one per universal rule (Rules #1-17).

📌 **Lower priority** — only worth it if you're actively iterating on coding standards.

---

### 📌 3.4 Cost / Token Tracking Per Feature

**What it is.** Tag conversations with the feature/epic they belong to, so you can attribute Anthropic API spend.

**Why it matters.** You can answer questions like "what did Epic 10 cost in tokens?" — useful for budgeting and for identifying features where Claude churned.

**How to implement.**

1. Convention: start each feature conversation with a header comment in the first user prompt:
   ```
   [Feature: studybuddy-epic-10-curriculum-governance]
   ```
2. Use the Anthropic API console / billing exports to attribute spend after the fact.
3. Lower priority unless you're paying significant API costs.

---

## 4. Risk Isolation

### ⚙️ 4.1 Worktree Isolation for Risky Experiments

**What it is.** Use the `isolation: "worktree"` parameter when launching sub-agents for changes you might not keep.

**Why it matters.** Lets you experiment on an isolated copy of the repo. If the experiment doesn't pan out, the worktree is auto-cleaned. Your main working directory stays clean.

**How to implement.**

1. For any "I wonder if we could…" exploration, launch the sub-agent with `isolation: "worktree"`.
2. Use cases:
   - Trying a different ORM (asyncpg → SQLModel) on a single endpoint
   - Refactoring the Celery task layout to a new package structure
   - Exploring whether to migrate from Kivy to Expo for the mobile client
3. The agent reports the worktree path and branch when done; cherry-pick what you want.

---

### ⚙️ 4.2 Background Long-Running Tasks

**What it is.** Use `run_in_background: true` for sub-agents and Bash commands that take more than a couple of minutes (load tests, large refactors, batch migrations).

**Why it matters.** You stay productive on the main thread instead of waiting. You're notified when the background task completes.

**How to implement.**

1. Suggested triggers for background mode:
   - Test runs > 2 minutes
   - Refactors that touch > 20 files
   - Load tests (k6, Locust)
   - Large data migrations (e.g., backfilling a new column)
2. Combine with worktree isolation for refactors.

---

## 5. Living Artefacts

### ⚙️ 5.1 Auto-Regenerated Architecture Index

**What it is.** A scheduled Claude job that re-reads the codebase and updates the 11 standard architecture diagrams (Rule #17) — diagram drift is otherwise silent.

**Why it matters.** Diagrams in `docs/architecture/` drift the moment a service moves between namespaces, an endpoint is renamed, or a queue is added. CI catches code drift; nothing catches diagram drift.

**How to implement.**

1. Use the `schedule` skill to run a job weekly:
   ```
   Re-read services/, infra/, and proto/. Compare against
   docs/architecture/*.md. For each of the 11 standard diagrams,
   identify drift. If drift found, propose an updated diagram and
   open a PR to docs repo with the diff.
   ```
2. Suggested cadence: weekly.
3. The job should produce a PR, not commit directly — diagrams need human review.

---

### ⚙️ 5.2 Claude-Written PR Descriptions With Reasoning

**What it is.** PR descriptions that include "what we considered and rejected," not just "what changed."

**Why it matters.** Your critique docs prove you think through alternatives — but that thinking is lost between conversation and merge. Capturing it in the PR description makes it durable.

**How to implement.**

1. Adopt this PR description template (codify as a slash command `/pr-description`):
   ```markdown
   ## What changed
   <one-paragraph summary>

   ## Why
   <the user-facing or technical reason>

   ## Alternatives considered
   - <option A> — rejected because <reason>
   - <option B> — rejected because <reason>

   ## Risk
   <what could go wrong, what we mitigated, what we accepted>

   ## Test plan
   - [ ] <bulleted manual / automated checklist>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   ```
2. The "alternatives considered" and "risk" sections are the differentiators — they're rare in normal PRs and high-value for future maintenance.

---

### 📌 5.3 Living `/onboarding` Slash Command

**What it is.** A slash command that walks a new contributor (or a fresh Claude session) through the project from scratch.

**Why it matters.** Replaces the missing `CONTRIBUTING.md` and gives Claude a single command to bootstrap context when starting a new conversation.

**How to implement.**

1. Create `.claude/commands/onboarding.md`:
   ```markdown
   ---
   description: Bootstrap context for a new session
   ---

   Read in order:
     1. README.md
     2. CLAUDE.md
     3. docs/architecture/01-system-design.md (if exists)
     4. docs/adr/index.md (if exists)
     5. The 5 most recently modified files in src/

   Then summarise:
     - What this project does (1 sentence)
     - The 3 most important architectural decisions
     - The 3 most active areas of recent change
     - Any known WIP / paused work
   ```
2. Use this at the start of any session that's been idle > 1 week.

---

## 6. Implementation Roadmap

A suggested order. Each phase is a long weekend or a focused week of effort.

### Phase 1 — Highest leverage (start here)

| # | Item | Effort | Impact |
|---|---|---|---|
| 1.1 | Spec-first prompt template + standard structure | 1 day | 🔥 Cuts re-work by ~30% |
| 1.2 | Plan mode discipline for ≥3-file changes | Habit only | 🔥 Catches design issues pre-code |
| 1.3 | Sub-agent fleet — `Explore` + `code-reviewer` defaults | Habit only | 🔥 Protects context, parallel work |
| 2.2 | Slash commands per project (`/new-endpoint`, `/new-adr`, `/new-migration`) | 1-2 days | 🔥 Codifies repeated workflows |

### Phase 2 — Automation

| # | Item | Effort | Impact |
|---|---|---|---|
| 2.1 | Hooks for ruff/eslint/alembic-check on file edits | 0.5 day | ⚙️ Fail-fast quality gates |
| 2.3 | `/done` and `/ship-ready` quality-gate commands | 0.5 day | ⚙️ Standardises "done" |
| 5.2 | `/pr-description` command with alternatives + risk sections | 0.5 day | ⚙️ Durable decision capture |

### Phase 3 — Cadence

| # | Item | Effort | Impact |
|---|---|---|---|
| 3.1 | Scheduled critique sub-agent (bi-weekly) | 0.5 day | ⚙️ Catches drift early |
| 3.2 | `DECISIONS.md` + `/log-experiment` command | 0.5 day | ⚙️ Captures dead ends |
| 5.1 | Scheduled diagram-drift PR generator | 1 day | ⚙️ Diagrams stay current |

### Phase 4 — Polish

| # | Item | Effort | Impact |
|---|---|---|---|
| 4.1 | Worktree isolation for experiments | Habit only | 📌 Cleaner main repo |
| 4.2 | Background mode for long-running tasks | Habit only | 📌 More parallel work |
| 5.3 | `/onboarding` slash command | 0.25 day | 📌 Faster session warm-up |
| 3.3 | Prompt eval suite for coding standards | 1 day | 📌 Only if iterating standards |
| 3.4 | Cost tracking per feature | Habit only | 📌 Only if API spend matters |

---

## Cross-Cutting Notes

**Skills you can use to implement these.** The Claude Code harness already ships with several skills that map directly to items above:
- `update-config` — for `.claude/settings.json` changes (hooks, permissions)
- `loop` — for self-paced recurring tasks
- `schedule` — for cron-based scheduled remote agents
- `simplify` — for periodic code review passes

**Anti-patterns to avoid.**
- Don't write hooks that are slow (>2s) — they add latency to every edit.
- Don't put project-specific commands in `~/.claude/commands/` — keep them per-repo so they version with the code.
- Don't run scheduled critique sub-agents more often than weekly — diminishing returns and noisy diffs.
- Don't write evals you won't re-run — write 5 you'll keep, not 50 you'll abandon.

**Single highest-leverage adoption.** If you only do one thing from this document: **spec-first prompts + plan mode (§1.1 + §1.2)**. Most of the bugs surfaced in v1.1 of both critiques (Stripe sync, JWKS TTL, `upsert_student` `account_status`, secret-tier confusion in Thittam) would have been caught at the design conversation rather than after implementation.
