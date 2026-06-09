# claude_memory (git-backed portable per-project Claude memory) — Design & Development Pattern

**Reviewed:** 2026-06-09 (v1.0 — first review)
**Reviewer:** Claude (Anthropic)
**Document type:** Development-pattern analysis (how this *tooling* was designed and evolved)
**Scope:** The problem it solves (Claude context loss across sessions/machines), the encoded-path convention, the hook-driven sync pattern, the growth to 10 repos, and the diagnose-twice-misdiagnosed history.
**Related:** [claude-memory-critique.md](claude-memory-critique.md) · [claude-memory-practices.md](claude-memory-practices.md) · [claude-memory-cost.md](claude-memory-cost.md)
**Sources:** `~/.claude/settings.json` (the Stop hook), the ten `~/.claude/projects/<encoded-path>/memory` repos, the runbooks `NEW_MACHINE_SETUP.md` + `claude-memory-add-project.md`, and the reference memory `reference_claude_memory_git_setup.md`.

---

> This is the *method* analysis — how a single founder turned an invisible Claude Code feature (per-project memory as loose local files) into a durable, version-controlled, cross-machine system, and how the design held up (and where it didn't) as it grew from a diagnosis to ten repos. The defining trait is **diagnosis-driven infrastructure**: the system was not designed up front; it was *reverse-engineered* from observed behavior, twice mis-read, then formalized — and the runbooks exist because the misdiagnosis was painful enough to write down.

---

## 1. The problem — Claude context evaporates between sessions and machines

Claude Code persists a small per-project "memory" (markdown files under `~/.claude/projects/<encoded-path>/memory/`, indexed by a `MEMORY.md` pointer with frontmatter `name`/`description`/`type` per file). Out of the box this memory has two failure modes:

1. **It's local-only.** It lives under `~/.claude` on one machine. A new laptop, a reinstall, or a second workstation starts from zero — the accumulated "here's what we decided, here's the bite that cost us an outage" context is gone.
2. **It's invisible and undifferentiated.** It looks like loose throwaway files, so the natural instinct is to treat it as disposable cache and either ignore it or propose "making it durable" from scratch — *not realizing it's already the system's working memory*.

The problem this tooling solves is therefore **durability + legibility of Claude's own cross-session memory**: make it survive machine changes, make it auditable (diffable, versioned), and make it unmistakably *not* loose files.

---

## 2. The diagnosis-driven origin (and the twice-misdiagnosed history)

The reference memory records the origin precisely: *"Diagnosed (and twice mis-diagnosed) on 2026-06-01."* That single line is the most important thing about how this system came to be. The pattern was:

1. **First misread:** the `~/.claude/projects/.../memory/` files look like loose, disposable local state.
2. **Second misread:** "we should make this durable" — i.e. proposing to *build* durability that, on closer inspection, already partly existed (the stores were git repos with remotes for some projects).
3. **Correct diagnosis:** the memory is *already* a durable, version-controlled, auto-pushed system — git repos on `main`, private GitHub remotes, driven by a `Stop` hook. The work was not to *build* durability but to **understand, formalize, complete, and document** it.

The reference memory bakes the lesson back in as a guardrail: *"Don't treat the memory dir as disposable local state, and don't propose making it 'durable' — it already is. When verifying memory state, check the repo level (`git -C <memory> status`), not just the file listing."* This is the system teaching its future self not to repeat the misdiagnosis — the misdiagnosis became a memory, which is itself the system working as intended.

**Method signal:** the artifact (the runbooks, the reference memory) is shaped by the *failure to understand it*, not by a clean upfront design. Good infra documentation often comes from exactly this — writing down the thing that confused you so it can't confuse you twice.

---

## 3. The encoded-path convention — the one load-bearing idea

The whole system hinges on a single deterministic transform: a project's memory dir name is its **absolute path with every `/` and `_` replaced by `-`**:

```bash
echo "$PWD" | sed 's|[/_]|-|g'
# /home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/thittam
#   -> -home-sivam-Documents-code-projects-AIStuff-STEM-studybuddy-thittam
```

This is elegant because it needs **no registry and no config**: the hook can compute the store path purely from `$PWD` at session end. It is also where two design properties come from:

- **cwd-keying as a feature.** Because the key is the cwd, `closedSpace` (a subdirectory of the `dronePrjs` repo) gets its *own* independent memory store — different cwd, different encoded path, different repo. The convention naturally supports nested projects.
- **absolute-path-keying as a liability.** The same transform embeds the username and layout (`-home-sivam-…`). On a different machine layout the encoded name changes and the hook looks elsewhere — the portability caveat the runbook documents at length (covered in the critique).

The convention is the system's cleverest and most consequential decision: one `sed` does the work a config file or a lookup table would otherwise need.

---

## 4. The hook-driven sync pattern

The automation is a single global `Stop` hook in `~/.claude/settings.json` (verified present, `async:true`, 30 s timeout):

```bash
M="$HOME/.claude/projects/$(echo "$PWD" | sed 's|[/_]|-|g')/memory"
[ -d "$M/.git" ] || exit 0
git -C "$M" add -A 2>/dev/null
if ! git -C "$M" diff --cached --quiet 2>/dev/null; then
  git -C "$M" commit -m "auto: memory snapshot $(date -u +%Y-%m-%dT%H:%MZ)" >/dev/null 2>&1 \
    && git -C "$M" push origin main >/dev/null 2>&1
fi
exit 0
```

The pattern is **capture-at-session-boundary**: after every response turn, snapshot whatever changed and push it. The design choices that make one global hook safe across every project:

- `[ -d "$M/.git" ] || exit 0` — a project with no memory repo is a clean no-op, so the hook can be global with zero per-project wiring.
- `diff --cached --quiet` — no empty commits; the `auto: memory snapshot <UTC>` commits only appear when memory actually changed.
- `exit 0` always — the hook can never fail or block a session.
- `async:true` + 30 s timeout — a slow push never stalls the user.

This is the right pattern for the goal (zero-effort capture) and the right *shape* (idempotent, no daemon). Its cost is the flip side of "never fails a session": every error is swallowed (`>/dev/null 2>&1`), which is the silent-failure gap analyzed in the critique and practices docs.

---

## 5. How it grew to ten repos

The system accreted one project at a time, and the commit histories show the growth and the usage gradient:

| Project (memory repo) | Commits | Note |
|---|---|---|
| `studybuddy-selflearner-memory` | 56 | Busiest — heaviest authoring activity |
| `studybuddy-memory` (OnDemand) | 23 | Second busiest; largest single file (23 KB `project_state.md`) |
| `project-critique-memory` | 9 | This very project |
| `mambakkam-net-memory` | 6 | |
| `MarketingTools-memory` | 3 | |
| `pramana-memory` | 3 | **All three commits dated 2026-06-09** — git-init'd only today |
| `wegofwd-llm-memory` | 3 | Added 2026-06-09 |
| `thittam-memory` | 1 | Initial snapshot only — no memory written for that cwd yet |
| `dronePrjs-memory` | 1 | Initial snapshot only |
| `closedSpace-memory` | 1 | Initial snapshot only (subdir of dronePrjs) |

The growth pattern is instructive:

- **Eight at 2026-06-01, ten by 2026-06-09.** The reference memory's table was written at "Eight projects wired in as of 2026-06-01"; `wegofwd-llm` and `pramana` were added 2026-06-09 (per the reference memory's own appended rows and the `wc -l`'d add-project runbook whose worked example *is* `wegofwd-llm`).
- **The add-a-project flow was formalized into a recipe** (`claude-memory-add-project.md`): `gh repo create --private` → `mkdir`/seed `MEMORY.md` → `git init -b main`/remote/commit → `ln -s` symlink. The global hook needs no change — "it just needs the repo + remote to exist." Growth is therefore O(1) hook + O(N) one-time per-project setup.
- **The 1-commit repos are initial-snapshot-only** — they exist and are protected, but no session has written memory for that exact cwd yet. This is the convention working: a store is created eagerly so the hook has somewhere to push, then fills in lazily.

---

## 6. The verification discipline that emerged

Two verification subtleties were discovered and written into the runbooks — both are method signals worth naming:

**6.1 "Verify shipped, not just committed."** A cross-cutting habit (its own reference memory) that applies here directly: a commit is not durable until it's *pushed*. The reference memory records a real instance — `project-critique` had advanced from another machine and a push was rejected non-fast-forward; the fix was `git fetch` + `git rebase origin/main`. The discipline: check the repo against its *remote* (`git -C <M> ls-remote origin main` vs `HEAD`), not just the local log.

**6.2 The `bash -c $PWD` reset gotcha.** `claude-memory-add-project.md` documents a genuine verification-correctness subtlety: *"Don't trust `bash -c 'echo $PWD'` — Bash resets `$PWD` to the real cwd on startup, so you must genuinely `cd` into the project dir to reproduce what a real session sees."* The verify recipe therefore does `( cd "$PROJ" && bash -c '<hook body>' )` and compares the GitHub SHA before/after. This was verified for `wegofwd-llm` on 2026-06-09 (remote advanced `de21f10 → a9424a3`, local HEAD == remote HEAD, test marker removed). The lesson: when you test a hook that keys off `$PWD`, you must reproduce the *exact* environment the hook runs in — a subshell that resets `$PWD` will silently test the wrong path.

---

## 7. The cross-machine habit

Because **only the memory repos auto-push** (via the Stop hook) and the **code repos do not**, the two drift apart between machines. The system's documented habit closes this: *"Always `git pull --rebase` before starting work on any project repo."* This is a deliberate asymmetry — memory is auto-durable, code is manually durable — and naming it prevents the trap of assuming everything syncs the way memory does.

---

## 8. Lessons this system teaches

1. **Reverse-engineer before you rebuild.** The biggest near-miss here was almost re-building durability that already existed. The fix was diagnosis, not construction — and writing the diagnosis down (incl. *that it was misread twice*) so it can't recur.
2. **A deterministic naming convention can replace a registry.** One `sed 's|[/_]|-|g'` lets a single global hook serve any number of projects with zero config — at the cost of binding the name to the absolute path.
3. **Make automation no-op-safe so it can be global.** The `[ -d "$M/.git" ] || exit 0` guard + `exit 0`-always is what lets one hook run after *every* session harmlessly.
4. **Capture at a natural boundary.** The session-end (`Stop`) hook snapshots exactly when there's something new to save, with a `diff --cached` guard against noise.
5. **Verify against the remote, and reproduce the hook's real environment.** "Committed ≠ pushed," and "`bash -c` resets `$PWD`" — both are written into the runbooks because both were learned the hard way.
6. **The same swallowed-error choice that makes the hook safe makes it silent.** This is the design's central tension (see the critique): never failing a session and never reporting a failure are the same `>/dev/null 2>&1` decision, and `pramana`'s un-init'd-for-days store is what that tension costs.

---

*This analysis is drawn from the on-disk hook (`~/.claude/settings.json`), the ten memory repos' commit histories and remotes (read directly on 2026-06-09), the two runbooks, and the reference memory `reference_claude_memory_git_setup.md` (which supplied the diagnosis history, the encoded-path rule, the ten-repo table, and the cross-machine habit). Commit counts and the `pramana` same-day history are measured, not asserted.*
