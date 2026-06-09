# claude_memory (git-backed portable per-project Claude memory) — Good Practices, Bad Practices & How to Improve

**Reviewed:** 2026-06-09 (v1.0 — first review)
**Reviewer:** Claude (Anthropic)
**Document type:** Engineering/operational practices analysis (for tooling/infra)
**Scope:** The Stop hook, the encoded-path convention, the per-repo durability model, the symlink view, the two runbooks, and the operational habits around them.
**Related:** [claude-memory-critique.md](claude-memory-critique.md) · [claude-memory-development-pattern.md](claude-memory-development-pattern.md) · [claude-memory-cost.md](claude-memory-cost.md)
**Rating key:** ✅ Good practice · ⚠️ Bad practice / risk · 🔧 How to improve

---

> A catalogue of concrete practices in the `claude_memory` tooling, measured on disk on 2026-06-09. The through-line: **the durability and documentation practices are strong; the gaps are all about silence** — the system never tells you when it isn't working, which is how a whole store (`pramana`) sat unprotected without anyone noticing, and how the privacy/portability caveats have no place to surface.

---

## ✅ Good Practices

### ✅ Durability via real remotes — the memory is genuinely backed up off-machine

Every memory store is a git repo with a **private** GitHub remote (verified: 10/10 `*-memory` repos are `PRIVATE` via `gh repo list`). The remote is treated as the source of truth, not a nice-to-have. This is the single best decision in the system: Claude's accumulated per-project context survives a lost laptop or a reinstall, and the restore is a documented clone.

🔧 *Takeaway:* if a tool produces state worth keeping, back it to a remote you don't control the uptime of — and treat the remote, not the local copy, as canonical.

### ✅ The hook is no-op-safe, so it can be global with zero per-project wiring

```bash
M="$HOME/.claude/projects/$(echo "$PWD" | sed 's|[/_]|-|g')/memory"
[ -d "$M/.git" ] || exit 0
... ; exit 0
```

The `[ -d "$M/.git" ] || exit 0` guard and the unconditional `exit 0` mean one global hook runs harmlessly after *every* session in *every* directory — no allowlist, no per-project config, no way to block or error a session. Adding a project requires no hook change at all.

🔧 *Takeaway:* a global hook should be a clean no-op everywhere it isn't supposed to act, and should never be able to fail the thing it's attached to.

### ✅ No-noise commits via a staged-diff guard

`if ! git -C "$M" diff --cached --quiet` means an `auto: memory snapshot <UTC>` commit only lands when memory actually changed. The histories prove it: the 1-commit repos (`thittam`, `dronePrjs`, `closedSpace`) are initial-snapshot-only — no churn, no empty commits.

### ✅ Deterministic, registry-free addressing

The `sed 's|[/_]|-|g'` encoded-path transform lets the hook find the right store from `$PWD` alone — no lookup table to maintain at runtime. cwd-keying also gives nested projects (`closedSpace` under `dronePrjs`) their own independent stores for free.

### ✅ The browse view can't be accidentally committed

The `_claude-memory-<project>` entries are **symlinks** living in the *non-repo workspace parent* (`STEM_studybuddy/`), explicitly so they "can never be accidentally committed into a code repo" (`claude-memory-add-project.md`). A convenience view that is structurally prevented from polluting a code repo is the right way to do a view.

### ✅ "Verify shipped, not just committed" is an enforced habit

The add-project runbook's verify recipe compares the **remote** SHA before/after (`git ls-remote origin main`) and asserts `HEAD == remote`, not just that a local commit exists. This caught a real non-fast-forward divergence on `project-critique` across two machines (reference memory), resolved with `git fetch` + `rebase`. Checking durability at the remote, not the commit, is exactly right for a push-based system.

### ✅ The system documents its own failure history

The reference memory records that this was *"Diagnosed (and twice mis-diagnosed)"* and bakes in the guardrail "don't treat the memory dir as disposable… check the repo level (`git -C <memory> status`), not just the file listing." Writing down the misdiagnosis so it can't recur is a mature documentation practice.

### ✅ Restore runbook hardened against a real failure

`NEW_MACHINE_SETUP.md` includes `mkdir -p "$(dirname "$sym")"` *because* `ln` failed without it when the workspace parent didn't yet exist — and says so. A runbook that records the specific footgun it hit is more useful than a clean-looking one that doesn't.

---

## ⚠️ Bad Practices / Risks

### ⚠️ Silent hook failure — the marquee risk, and it has already bitten

Every git operation in the hook is `>/dev/null 2>&1`, the hook is `async`, and it `exit 0`s unconditionally. A failed commit, a rejected push, an expired token, or a **missing `.git`** all produce *zero* signal.

**This is not theoretical: `pramana`'s memory dir existed with four real files but was never `git init`'d, so the global hook silently no-op'd for it** — its memory was machine-local-only, with no remote, until it was init'd today. Confirmed: the `pramana-memory` repo's entire history is three commits, all 2026-06-09. A store can be unprotected indefinitely and nothing tells you.

🔧 **Fix (cheap, high-value):** append a one-line outcome to a log on every run —
```bash
echo "$(date -u +%FT%TZ) $M $(git -C "$M" rev-parse --short HEAD 2>/dev/null || echo NO-GIT) ${pushresult:-?}" >> "$HOME/.claude/memory-sync.log"
```
and add a `claude-memory-doctor` that lists every `~/.claude/projects/*/memory` dir and flags any that (a) lack `.git`, (b) lack a remote, or (c) have local commits ahead of `origin`. That single check would have caught `pramana` the day it diverged.

### ⚠️ No redaction before push — memory is pushed verbatim

The hook does `git add -A` with no secret scan. The on-disk content is genuinely operational (probed via `grep`/`find`): hosting cost figures, a Cloudflare Origin-Cert SAN mismatch that "caused a 526 outage during the 2026-05-18 launch," Gmail/SMTP send-as config, the operator's identity, and where the Anthropic invoice PDFs live. None of that is a credential — but **nothing prevents an actual secret** (a pasted key, a token in a captured stack trace) from being committed and pushed if Claude ever writes one into a memory file.

🔧 **Fix:** add a pre-commit secret scan to the hook — abort + warn if staged content matches `sk-ant-|gho_|AKIA|-----BEGIN`. Coarse is fine; it closes the worst case.

### ⚠️ One broad token gates all ten private repos

`gh auth status` shows a single `gho_…` token with `repo` scope in the keyring. That one token can read **and force-push** every `*-memory` repo. No per-repo deploy key, no fine-grained PAT scoped to just these repos. A single leak exposes and could rewrite history on all ten at once.

🔧 **Fix:** issue a **fine-grained PAT** scoped to only the `*-memory` repos for the push path, shrinking the blast radius from "every repo the account owns" to "just the memory repos."

### ⚠️ No fetch/rebase before push — cross-machine divergence is swallowed

The hook pushes without first integrating remote changes. Two machines (or two concurrent sessions) working the same project produce a non-fast-forward rejection that the hook silently discards — the local commit lands, the remote doesn't, and only a manual `ls-remote` reveals it. The reference memory confirms this happened on `project-critique`.

🔧 **Fix:** on push failure, attempt `git -C "$M" pull --rebase origin main && git -C "$M" push` once, and log the outcome either way. (Still keep `exit 0` so a session is never blocked.)

### ⚠️ No encryption at rest beyond GitHub's

Memory is plain markdown in private repos — confidentiality rests entirely on GitHub's access control plus the one token's secrecy. Acceptable for a personal setup; worth naming as the explicit trust assumption.

🔧 **Fix (only if a store must hold a real secret):** `git-crypt` or `age`-encrypt that specific file before commit.

### ⚠️ Absolute-path-keyed encoded path — portability requires manual reconciliation

`sed 's|[/_]|-|g'` over the absolute path bakes in the username/layout (`-home-sivam-…`). A different machine layout silently resolves a different (non-existent) store and the hook no-ops. The runbook documents this under "Path dependency (important)," but the system can't enforce it.

🔧 **Fix:** the doctor check (above) run right after a new-machine restore would flag any project whose encoded dir doesn't exist, catching a layout mismatch before it loses a session's memory.

### ⚠️ Restore is list-driven and the runbook counts have drifted

The clone-all loop hard-codes ten `project|repo|symlink` triples, and the prose still says "8 repos" / "Eight projects wired in" in places (the system is now at 10). A hand-maintained list drifts from reality as projects are added.

🔧 **Fix:** make restore data-driven — `gh repo list wegofwd2020-hub --json name -q '.[]|select(.name|endswith("-memory"))'` to discover every store, rather than maintaining a MAP by hand.

---

## 🔧 Prioritized improvements

| Priority | Improvement | Closes |
|---|---|---|
| **P1** | Add a sync **log line** + a `claude-memory-doctor` (flag no-`.git` / no-remote / ahead-of-origin) | The silent-failure + `pramana`-class reliability gap; also surfaces portability mismatches |
| **P1** | **Pre-commit secret scan** in the hook (`sk-ant-`/`gho_`/`AKIA`/`BEGIN`) | The "Claude writes a real key into memory and it's pushed" path |
| **P2** | **Fine-grained PAT** scoped to `*-memory` repos for the push path | The one-token-exposes-all-ten blast radius |
| **P2** | **`pull --rebase` retry on push failure**, logged | Swallowed cross-machine non-fast-forward divergence |
| **P3** | **Data-driven restore** off `gh repo list … endswith("-memory")` | List drift; refresh the runbooks' "8"→"10" counts |
| **P3** | `git-crypt`/`age` only if a store must hold a real secret | No-encryption-at-rest, for the narrow case that needs it |

---

## Bottom line

The durability, no-op-safety, no-noise-commit, and verify-shipped practices are genuinely good and right-sized for personal DX infra. Every material risk traces to one root: **the hook is silent.** Closing that with a single log line plus a `doctor` check is the highest-leverage change — it directly retires the `pramana`-class reliability gap and gives the privacy/portability caveats somewhere to show up. The secret-scan and fine-grained-PAT changes are the next tier, shrinking the privacy/blast-radius exposure that "private repos" alone doesn't cover.

---

*Practices measured on disk on 2026-06-09 from `~/.claude/settings.json`, the ten memory repos (status/remotes/commit counts read directly), `gh repo list`/`gh auth status`, the on-disk memory content (`grep`/`find` probe), and the two runbooks. The `pramana` silent-no-op is corroborated by the reference memory and the repo's three-commit, single-day history.*
