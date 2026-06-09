# Adding a project to git-backed portable Claude memory

This documents the system that lets each project's Claude per-project memory survive
machine changes, and the exact steps used to wire in a new project. Worked example:
**`wegofwd-llm`** (added 2026-06-09).

## What the system is

There is no product name — it's **git-backed portable per-project Claude memory**. Four parts:

| Part | What it is | Source of truth? |
|---|---|---|
| **Canonical store** | `~/.claude/projects/<encoded-path>/memory/` — its own git repo on `main` | **Yes** |
| **Remote** | Private `github.com/wegofwd2020-hub/<name>-memory.git` — the off-machine durability | Mirror |
| **Auto-sync** | Global `Stop` hook in `~/.claude/settings.json`: after every session, `add → commit → push` | — |
| **Workspace symlink** | `STEM_studybuddy/_claude-memory-<name>` → the memory dir, for easy browsing | No (just a view) |

The `_claude-memory-<project>` folders are **only symlinks** (a convenience view). They live
in the non-repo workspace parent so they can never be accidentally committed into a code repo.

### Encoded path

The memory dir name is the project's absolute path with every `/` **and** `_` replaced by `-`:

```bash
echo "$PWD" | sed 's|[/_]|-|g'
# /home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/wegofwd-llm
#   → -home-sivam-Documents-code-projects-AIStuff-STEM-studybuddy-wegofwd-llm
```

### The Stop hook (already global — no per-project change needed)

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

The hook derives the path from `$PWD`, so it only acts when a real Claude session runs **inside
the project dir**. It needs nothing more than the repo + remote to exist.

## Steps to add a new project

Replace `wegofwd-llm` / the path below with your project.

```bash
PROJ="/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/wegofwd-llm"
NAME="wegofwd-llm"
ENC="$(echo "$PROJ" | sed 's|[/_]|-|g')"
MEM="$HOME/.claude/projects/$ENC/memory"
SYM="$(dirname "$PROJ")/_claude-memory-$NAME"   # parent must NOT be a git repo

# 1. create the private remote (gh authed as wegofwd2020-hub)
gh repo create "wegofwd2020-hub/${NAME}-memory" --private

# 2. local memory dir + seed index
mkdir -p "$MEM"
: > "$MEM/MEMORY.md"

# 3. init, wire remote, first commit, push
git -C "$MEM" init -b main
git -C "$MEM" remote add origin "https://github.com/wegofwd2020-hub/${NAME}-memory.git"
git -C "$MEM" add -A
git -C "$MEM" commit -m "chore: initial snapshot of Claude memory"
git -C "$MEM" push -u origin main

# 4. workspace symlink (the browsable view)
ln -s "$MEM" "$SYM"
```

## Verifying the next session will auto-push

Don't trust `bash -c 'echo $PWD'` — **Bash resets `$PWD` to the real cwd on startup**, so you must
genuinely `cd` into the project dir to reproduce what a real session sees. Compare the GitHub SHA
before/after running the hook body:

```bash
PROJ="/home/sivam/Documents/code/projects/AIStuff/STEM_studybuddy/wegofwd-llm"
MEM="$HOME/.claude/projects/$(echo "$PROJ" | sed 's|[/_]|-|g')/memory"

git -C "$MEM" ls-remote origin main          # remote SHA BEFORE
echo "test" > "$MEM/_hook_verify.tmp"         # simulate a session writing memory

( cd "$PROJ" && bash -c '<the Stop-hook body above>' )

git -C "$MEM" ls-remote origin main          # remote SHA AFTER — must advance
[ "$(git -C "$MEM" rev-parse HEAD)" = "$(git -C "$MEM" ls-remote origin main | cut -f1)" ] \
  && echo "in sync — pushed" || echo "NOT pushed"

rm "$MEM/_hook_verify.tmp"                     # clean up the marker afterward
```

**Verified for `wegofwd-llm` on 2026-06-09:** hook saw `PWD=.../wegofwd-llm`, resolved the correct
memory path, committed and pushed; remote advanced `de21f10 → a9424a3`, local HEAD == remote HEAD.
Test marker removed afterward; repo tracks only `MEMORY.md`.

## New-machine recovery

Memory repos auto-push; **code repos do not**. On a fresh box:

```bash
git clone "https://github.com/wegofwd2020-hub/${NAME}-memory.git" \
  "$HOME/.claude/projects/<encoded-path>/memory"
ln -s "$HOME/.claude/projects/<encoded-path>/memory" "$(dirname "$PROJ")/_claude-memory-$NAME"
```

Then the global Stop hook keeps it synced. The full multi-project runbook (hook JSON + clone-all +
symlink script) lives as `NEW_MACHINE_SETUP.md` in the `wegofwd2020-hub/project-critique` repo —
clone that first on a new machine.

> Habit: `git pull --rebase` before working on any **code** repo — those drift between machines
> since only the memory repos auto-push.
