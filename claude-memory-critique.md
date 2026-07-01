# claude_memory (git-backed portable per-project Claude memory) — System Design Critique

**Reviewed:** 2026-06-09 (v1.0 — first review)
**Reviewer:** Claude (Anthropic)
**Scope:** The *system design* of the portable per-project Claude memory tooling — not an application. Architecture, robustness, security/privacy, portability, observability, maintainability, scalability (10 → N repos). Measured on disk on 2026-06-09 against `~/.claude/settings.json`, all ten `~/.claude/projects/<encoded-path>/memory/` git repos, the `wegofwd2020-hub/*-memory` remotes (via `gh`), and the two runbook docs `NEW_MACHINE_SETUP.md` (141 lines) + `claude-memory-add-project.md` (117 lines).
**Rating key:** 🟢 Strong · 🟡 Adequate / has gaps · 🔴 Material risk

---

## What this system is (two sentences)

`claude_memory` is a git-backed durability layer for Claude Code's per-project memory: each project's memory lives in its own git repo under `~/.claude/projects/<encoded-path>/memory/`, and a single global `Stop` hook in `~/.claude/settings.json` auto-commits and pushes that repo to a private `github.com/wegofwd2020-hub/<name>-memory` remote after every session. The remotes are the source of truth that lets a project's Claude context be reconstructed on a fresh machine; ten projects are wired in, all remotes private, with workspace symlinks (`_claude-memory-<project>`) as a browse-only view.

This is **infrastructure/tooling**, not a product — a few-dozen-line shell hook plus a convention plus two runbooks. It should be judged as small DX infra: is it durable, safe, portable, and observable? It is mostly durable and well-documented, with two real gaps — **silent hook failure** and **no redaction/encryption of memory content** — that this review weights honestly rather than inflates.

---

## Measured facts (2026-06-09)

| Fact | Value | How measured |
|---|---|---|
| Memory repos (git-init'd stores) | **10** | `ls ~/.claude/projects/` + per-dir `[ -d memory/.git ]` |
| Of which PRIVATE on GitHub | **10 / 10 (all private)** | `gh repo list wegofwd2020-hub --json name,visibility -q '…endswith("-memory")'` |
| Stop hook present + `async:true` | **Yes** (single global hook) | `grep -A8 '"Stop"' ~/.claude/settings.json` |
| Hook timeout | 30 s | settings.json |
| Remote transport | HTTPS (token via `gh` keyring) | `git remote -v`; `gh auth status` → `keyring` |
| Token scopes | `gist, project, read:org, repo, workflow` | `gh auth status` |
| Total on-disk memory | ~236 KB, ~100 `.md` files | `du`, `find` |
| Largest single memory file | 23 KB (`StudyBuddy-OnDemand/project_state.md`) | `find -printf` |
| Busiest store | `mentible-memory` (56 commits) | `git rev-list --count` |
| Quietest stores | `thittam`, `dronePrjs`, `closedSpace` (1 commit = initial snapshot only) | same |
| Runbook docs | `NEW_MACHINE_SETUP.md` 141 ln · `claude-memory-add-project.md` 117 ln | `wc -l` |

The encoded path is the project's absolute path with every `/` **and** `_` replaced by `-`:
`echo "$PWD" | sed 's|[/_]|-|g'`. The hook recomputes this from `$PWD` at session end, so the memory dir must sit at exactly that name for the hook to find it.

---

## Ratings summary

| Area | Rating | One-line finding |
|---|---|---|
| Architecture | 🟢 Strong | Dead-simple, idempotent, no daemon/service — git + one hook + a naming convention; remotes as source of truth is the right durability model |
| Robustness | 🟡 Gaps | Hook is best-effort and **silent** (`>/dev/null 2>&1`, `async`); a store missing `.git` is a no-op that loses nothing locally but never reaches a remote — this actually happened to `pramana` |
| Security / Privacy | 🟡 Gaps | All 10 remotes private (good), but **no redaction before push and no encryption at rest** — memory holds real operational internals; one leaked `repo`-scoped token exposes all 10 |
| Portability | 🟡 Gaps | Restore-on-new-machine is documented and verified, but the encoded path is derived from the **absolute path** → breaks on a different username/layout (the runbook flags this) |
| Observability | 🔴 Weak | No success/failure signal anywhere; the only way to know a store synced is to manually `git -C <M> status` / `ls-remote` per repo; failures are invisible by design |
| Maintainability | 🟢 Strong | One hook, two runbooks, a reference memory documenting the whole thing incl. the diagnosis history; adding a project is a 4-step recipe |
| Scalability (10→N) | 🟡 Adequate | Linear and fine to dozens; the un-enumerated cost is N separate repos to create/clone/verify by hand — no `for`-loop registry beyond the runbook's hard-coded MAP |

---

## 1. Architecture — 🟢 Strong

**The design is correct and minimal.** There is no daemon, no sync service, no database — just three primitives:

1. **Canonical store** = a normal git repo at `~/.claude/projects/<encoded-path>/memory/`.
2. **Durability** = a private GitHub remote per store (the source of truth).
3. **Automation** = one global `Stop` hook that does `add -A → commit → push` only if there's a staged diff.

This is the right shape for the problem. Git gives versioning, diffing, and conflict detection for free; GitHub gives off-machine durability; the hook gives zero-effort capture. The hook body is genuinely idempotent and no-op-safe:

```
M="$HOME/.claude/projects/$(echo "$PWD" | sed 's|[/_]|-|g')/memory"
[ -d "$M/.git" ] || exit 0                         # not a memory repo → exit clean
git -C "$M" add -A 2>/dev/null
if ! git -C "$M" diff --cached --quiet 2>/dev/null; then
  git -C "$M" commit -m "auto: memory snapshot $(date -u +%Y-%m-%dT%H:%MZ)" >/dev/null 2>&1 \
    && git -C "$M" push origin main >/dev/null 2>&1
fi
exit 0
```

The `[ -d "$M/.git" ] || exit 0` guard is what makes one global hook safe across every project (including those with no memory repo). The `diff --cached --quiet` guard means no empty commits. `exit 0` unconditionally means the hook never blocks or errors a session. These are all the right choices.

**Notable design wins.**
- **`$PWD`-derived path** means the hook is fully generic — no per-project config; adding a project needs only the repo + remote to exist.
- **Symlinks live in the non-repo workspace parent** (`STEM_studybuddy/`), so the browse view can never be accidentally committed into a code repo (documented intent in `claude-memory-add-project.md`).
- **`closedSpace` is keyed off cwd**, so a subdirectory of the `dronePrjs` repo correctly gets its own independent memory store — the cwd-keying is a feature, not a bug.

### Gaps & risks

🟡 **The same `$PWD`-keying that makes the hook generic also makes it brittle to *where you launch Claude from*.** The store is bound to the exact cwd; launching a session from a parent or child directory resolves a *different* (likely non-existent) encoded path, and the hook silently no-ops. This is correct behavior, but it means "did my memory get saved?" depends on cwd discipline the system never checks.

🟡 **No write-side ordering / locking.** Two concurrent sessions in the same project cwd both run the Stop hook against the same repo. The second push can be rejected non-fast-forward (the reference memory records exactly this for `project-critique` across two machines). The hook does not fetch/rebase before push, so a rejected push is simply swallowed — the local commit lands, the remote does not, and nothing tells you.

---

## 2. Robustness — 🟡 Gaps

**The headline reliability finding: the hook is silent, and silence has already cost a real store.** Every failure path in the hook is `>/dev/null 2>&1` and the hook is `async`, so a failed `commit` or a rejected `push` produces **no signal** — not in the session, not in a log, nowhere. Combined with the `[ -d "$M/.git" ] || exit 0` guard, a memory dir that exists but was never `git init`'d is indistinguishable (to the user) from one that is syncing fine.

**This is not hypothetical.** `pramana` had a memory dir with four real files that was **never git-init'd**, so the global Stop hook had been silently no-op'ing for it — its memory was machine-local only, with no remote, for an unknown period until it was finally init'd today. Verified: the `pramana-memory` repo's *entire* history is three commits, all stamped 2026-06-09 (`036c6dd` "initial snapshot" → first `auto: memory snapshot` → marker cleanup), confirming the repo did not exist off-machine before today. A store can sit un-protected indefinitely and the system will never tell you.

### Other robustness notes

- 🟡 **Non-fast-forward push is swallowed.** No fetch/rebase before push; a cross-machine divergence silently fails the push (reference memory confirms this happened and had to be resolved by hand with `git fetch` + `git rebase origin/main`).
- 🟡 **Network/auth failure is swallowed.** If the token is expired or the network is down at session end, the commit lands locally but the push fails silently — durability is lost until the *next* successful session push happens to carry it.
- 🟢 **But local data is never at risk.** Because the canonical store is a local git repo, nothing is *lost* on push failure — it's just not *durable* yet. The failure mode is "not backed up," not "destroyed." That materially lowers the severity of every silent-failure case above.
- 🟢 **30 s timeout + async** means a slow push never hangs a session.

**The fix is cheap:** a single observability affordance (below) would convert every silent failure into a visible one.

---

## 3. Security / Privacy — 🟡 Gaps

**Good: all ten remotes are private.** Verified via `gh repo list` — every `*-memory` repo is `PRIVATE`. That is the correct default and it is held consistently across all ten.

**The honest gaps:**

🟡 **No redaction before push.** The hook does `git add -A` and pushes verbatim — whatever Claude wrote into a memory file goes to GitHub unmodified. There is no scrubber, no allowlist, no secret-pattern filter. A probe of the on-disk memory shows the content is genuinely operational: hosting cost numbers verified against a Hetzner console quote, a Cloudflare Origin-Cert/SAN mismatch that caused a "526 outage during the 2026-05-18 launch," Gmail send-as / SMTP configuration notes, the operator's identity and "where Siva's Anthropic invoice tracker and PDFs live," and per-project architecture. None of that is a *credential*, but it is exactly the operational internals a private repo is supposed to contain — and there is no mechanism preventing an *actual* secret (a pasted key, a token in a stack trace) from being captured and pushed if Claude ever writes one into memory.

🟡 **No encryption at rest beyond GitHub's.** The memory is stored as plain markdown in GitHub-hosted private repos. There is no client-side encryption envelope. The confidentiality of all ten stores rests entirely on (a) GitHub's access control and (b) the secrecy of one OAuth token.

🔴 **Blast radius of a single token.** `gh auth status` shows one `gho_…` token with `repo` scope in the local keyring. That one token can read **and force-push** all ten private memory repos. There is no per-repo deploy key, no fine-grained PAT scoped to just these repos, no MFA-gated push path. A single leaked token exposes (and could rewrite history on) every store at once. For a personal-founder setup this is an accepted trade-off, but it is the system's largest single point of compromise and is rated accordingly.

### Recommendations
- Add a pre-push **secret scan** to the hook (e.g. `grep -E 'sk-ant-|gho_|AKIA|-----BEGIN'` over staged content; abort + warn on a hit). Even a coarse filter closes the "Claude accidentally wrote a key into memory" path.
- Consider a **fine-grained PAT** scoped to only the `*-memory` repos instead of the broad `repo`-scoped `gho_` token, to shrink the blast radius.
- If any store ever needs to hold a genuine secret, encrypt that file client-side (`git-crypt` / `age`) before it's committed.

---

## 4. Portability — 🟡 Gaps

**Restore-on-new-machine is real, documented, and verified.** `NEW_MACHINE_SETUP.md` is a complete runbook: recreate the hook (full JSON given), clone all ten repos into their encoded paths via a hard-coded `MAP`, recreate the symlinks. It was verified end-to-end in a temp dir on 2026-06-01 ("all 8 repos clone with auth, and the symlinks resolve"). The runbook even hardens the failure it hit — `mkdir -p "$(dirname "$sym")"` is required or `ln` fails when the workspace parent isn't present yet.

**The portability gap is structural:** 🟡 the encoded path is derived from the project's **absolute path**, so it embeds the username and directory layout (`-home-sivam-Documents-code-projects-…`). On a machine with a different username (`/home/otheruser/…`) or a different folder structure, `sed 's|[/_]|-|g'` produces a *different* encoded dir name, and the hook looks in the wrong place. The runbook flags this explicitly under "Path dependency (important)" and gives two outs: replicate the same absolute paths, or recompute the encoded path with `enc()` and clone there. The symlink targets are absolute too and must be regenerated, not copied. So the system *is* portable, but only with manual reconciliation — it is not layout-independent.

🟡 **The restore is also a manual, list-driven process.** The clone-all loop hard-codes the ten `project|repo|symlink` triples. There is no discovery step (e.g. "clone every `*-memory` repo the account owns"), so the list and the runbook must be kept in sync as projects are added — and adding `wegofwd-llm` / `pramana` today means the runbook's "8 repos" verification text already lags the actual 10.

---

## 5. Observability — 🔴 Weak

This is the weakest area and the root cause of the robustness gaps. There is **no signal** that the system is working:

- The hook writes nothing to any log on success or failure.
- There is no "last synced" timestamp surfaced anywhere a human looks.
- The only way to audit health is to manually iterate all ten repos (`git -C <M> status` / `git -C <M> ls-remote origin main` and compare to `HEAD`) — which is exactly what the runbook's "Verify" block does, and exactly why `pramana`'s un-init'd state went unnoticed.

A single cheap affordance would fix most of §2: append a one-line outcome (path, commit SHA or "no-op" or "PUSH FAILED") to `~/.claude/memory-sync.log`, and/or drop a `.last_push` marker. Even better, a `claude-memory-doctor` one-liner that lists every `~/.claude/projects/*/memory` dir and flags any that (a) lack `.git`, (b) lack a remote, or (c) have local commits ahead of origin — that single check would have caught `pramana` immediately.

---

## 6. Maintainability — 🟢 Strong

**For its size this is well-maintained.** The whole system is one hook + two runbooks + a reference memory. The reference memory (`reference_claude_memory_git_setup.md`) documents the encoded-path rule, the full ten-repo table, the cross-machine `git pull --rebase` habit, and even the **diagnosis history** ("Diagnosed (and twice mis-diagnosed) on 2026-06-01") — capturing *why* the misdiagnoses happened (treating durable git-backed stores as "loose files"). Adding a project is a clean 4-step recipe (`gh repo create --private` → `mkdir`/seed `MEMORY.md` → `git init`/remote/commit/push → `ln -s`), and the hook needs no per-project change.

🟡 The one maintainability debt is **doc drift in the runbooks themselves**: both still describe "8 repos" / "clone-all-8" in places while the system is now at 10 (the reference memory's repo table *is* current at 10, but the `NEW_MACHINE_SETUP.md` verify text and the reference memory's own "Eight projects wired in" line lag). The MAP block in the runbook does list all 10 — so a restore would work — but the prose counts are stale.

---

## 7. Scalability (10 → N) — 🟡 Adequate

The per-session cost is one `add`/`diff`/`commit`/`push` against one small repo — trivially fine to dozens or hundreds of projects. The store sizes are tiny (~236 KB total, largest file 23 KB). Nothing in the runtime path scales with N; the hook only ever touches the one repo matching `$PWD`.

The cost that *does* grow linearly with N is **operational, not runtime**: every new project is a manual `gh repo create` + init + symlink, and every new machine is N manual clones driven by a hard-coded MAP. At 10 this is fine. At 30+ the absence of a discovery/registry step (clone-every-`*-memory`-repo; enumerate-every-`memory`-dir) starts to bite — both the add-project flow and the restore flow would benefit from being data-driven off `gh repo list … endswith("-memory")` rather than a hand-maintained list.

---

## Top findings (ordered)

1. 🔴→🟡 **Silent hook failure is the top reliability gap, and it has already bitten.** `pramana` sat with a non-git-init'd memory dir while the global hook silently no-op'd; its memory was machine-local-only with no remote until it was init'd today (confirmed: `pramana-memory`'s entire history is three commits, all 2026-06-09). The fix is one log line + a `doctor` check.
2. 🟡 **No redaction or at-rest encryption; one token gates all ten private repos.** Remotes are correctly private, but memory is pushed verbatim (real operational internals observed on disk) with no secret scan, and a single `repo`-scoped token can read and force-push every store.
3. 🟡 **Absolute-path-keyed encoded path makes portability a manual reconciliation**, not a layout-independent restore — correctly documented as a caveat, but a caveat the system can't enforce.

**Bottom line:** this is small, durable, honestly-documented DX infrastructure that does its core job (off-machine memory durability) well, with a clear single highest-value improvement — **make the hook observable** (one log line + a doctor check), which simultaneously closes the silent-failure reliability gap and gives the privacy/portability caveats a place to surface.

---

*Point-in-time review measured on 2026-06-09 against `~/.claude/settings.json`, the ten `~/.claude/projects/<encoded-path>/memory` git repos (commit counts, remotes, status all read directly), `gh repo list wegofwd2020-hub` (visibility) and `gh auth status` (token scopes), the on-disk memory content (privacy probe via `grep`/`find`), and the two runbooks `NEW_MACHINE_SETUP.md` (141 ln) + `claude-memory-add-project.md` (117 ln). The `pramana` silent-no-op finding is corroborated by the reference memory `reference_claude_memory_git_setup.md` and by `pramana-memory`'s three-commit, single-day history. No remote content was inspected beyond visibility metadata.*
