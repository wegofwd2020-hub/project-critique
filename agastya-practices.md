# AGASTYA — Good Practices, Bad Practices & How to Improve

<!-- doc-meta:start -->
| Field | Value |
|---|---|
| Product repo | `wegofwd2020-hub/agastya` |
| Branch | `main` |
| Git commit | `2abde5a` (as of 2026-08-10) |
| Product version | —  (commit-based; no release version) |
| Doc updated | 2026-09-03 |
| Last deployed | not deployed — live demo in progress (blocked on DNS) |
<!-- doc-meta:end -->

**Document type:** Engineering practices analysis (general practices only)
**Scope:** A FastAPI cyber-monitoring package adopted from an external AI-generated delivery, then imported, verified, corrected, and wrapped for a public read-only demo. Reviewed against `origin/main` at `2abde5a` (2026-08-10), measured 2026-09-02.
**Related:** `agastya-development-pattern.md`
**Rating key:** ✅ Good practice · ⚠️ Bad practice · ❌ Critical issue · 🔧 How to improve
**Note:** AGASTYA is a live-intended cyber-detection product, so this public document covers **general engineering practices only** — the kind of lesson that transfers to any project. It contains no product-specific security assessment, no map of what the detector does or doesn't catch, and no exploit paths; those are held in the private critique. Where a practice below touches security, it is stated as a general principle, not as a description of this system's defenses.

---

## Table of Contents

1. Adoption & Verification Practices
2. Architecture & Seam Practices
3. Demo & Deploy-Safety Practices
4. Code-Quality Practices
5. Testing Practices
6. Operational Practices

---

## 1. Adoption & Verification Practices

### ✅ Good — Treat a delivered quality claim as unverified until you reproduce it
The package arrived claiming a passing test suite; the adoption re-ran the suite from the repo root and reported the output verbatim rather than inheriting the claim. That discipline is what surfaced the real state of the code. For any handed-over artifact — and especially machine-generated code, whose prose is written with the same confidence whether or not it matches the code — a claim about the code is not evidence about the code.
🔧 **Keep doing this:** make "we ran it and here is the output" the acceptance gate, never "the author says it passes."

### ✅ Good — Land each defect fix with its own regression test
Delivered defects that were fixed during the import each shipped with a test that pins the corrected behavior. This is the right conversion of a one-time fix into a permanent guarantee.

### ✅ Good — State the scope boundary explicitly ("rehabilitate, don't rewrite")
The import spec names, in writing, that it would not re-architect the inherited code. A stated boundary lets every later reader understand the disposition of the artifact — a triage-and-ship, not a rebuild — instead of guessing.
🔧 **Generalize:** when you adopt code you won't fully rebuild, write down how deep the intervention goes. An unstated boundary reads as an accident; a stated one reads as a decision.

### ⚠️ Bad — Inherited docs that oversell were left in place alongside a corrected README
The reader-facing README was pulled back to the truth, which is excellent — but other inherited docs still carry "production-ready" and "✅ complete" language for capabilities that are shallower than the labels imply. Mixed signals in the same repo are worse than either signal alone.
🔧 **How to improve:** when you correct the top-level description, sweep the secondary docs to match, or mark them superseded. One honest surface and several overselling ones net out to "unreliable docs."

## 2. Architecture & Seam Practices

### ✅ Good — Make two things that must behave identically share one implementation
A single event-processing function is called by both the live endpoint and the demo seeder, so the two cannot drift. This is the correct way to guarantee "the demo runs what the endpoint runs": remove the *possibility* of divergence rather than policing it with discipline.
🔧 **Generalize:** whenever a requirement is "X and Y must do the same thing," collapse X and Y to one implementation with two callers.

### ⚠️ Bad — Configuration that the code it configures never reads
A config module defines scoring weights, category lists, and a `validate()` that checks them — but the engine hardcodes the same values inline and never consults the config object. Two sources of truth, one of them dead. A future maintainer who tunes the config will change nothing and be misled by the fact that `validate()` passes.
🔧 **How to improve:** either wire the engine to read the config (single source of truth) or delete the unused config so it cannot mislead. A configuration surface that has no effect is worse than none.

### ⚠️ Bad — Shipped modules that no caller reaches
A significant share of the package's modules are imported only by their own tests — reachable from no running entry point and absent from the package's public exports. They are tested, which makes them *look* live, but nothing invokes them. Dead-but-tested code is especially deceptive because the green suite implies it is in use.
🔧 **How to improve:** wire it or cut it. Either expose the module through a real entry point or move it out of the shipped package. If it is genuinely roadmap, keep it on a branch, not in `main` presented as delivered capability.

### ⚠️ Bad — Rely on a network-layer control where an application-layer control is the durable one
The public demo's safe (read-only) posture is enforced in several independent layers, which is genuinely good defense in depth. The general caution — true of any service — is that a proxy or environment toggle protects only the deployment that happens to have it; the application's own behavior is the control that travels with the code everywhere it runs.
🔧 **How to improve (general principle):** put the authoritative guarantee in the application, and treat the network layer as reinforcement, not as the primary control. Defense in depth means the app is still correct if the outer layer is misconfigured.

## 3. Demo & Deploy-Safety Practices

### ✅ Good — Generate demo data through the real code path
The demo dataset is produced by replaying scenarios through the same pipeline the live endpoint uses, so it is genuine derived output, not a hand-written fixture that can drift into flattering fiction. A demo built this way *is* evidence of what the system does.

### ✅ Good — Fail closed when the demo would be empty-but-healthy
The seeder refuses to start if it would leave any store empty. An empty demo that still reports "healthy" is a silent failure that looks fine; converting it into a visible crash-loop is the right instinct — make the bad state loud.
🔧 **Generalize:** any "healthy" signal should be backed by a check that the thing it claims is actually true.

### ✅ Good — Make the safe posture the image's default, not an external file's job
The read-only default is baked into the container image itself, so a bare `docker run` cannot bypass it by skipping a compose file. Defaults should be safe; unsafe should require a deliberate override.

### ✅ Good — Keep the app's advertised surface consistent with what the deployment allows
When the deployment disables write operations, the app also removes those routes from its own API and its generated schema — so the documentation the app serves matches what the deployment will actually answer. Consistency between "what the docs say you can do" and "what the server will do" is a real usability and trust property.

## 4. Code-Quality Practices

### ✅ Good — Typed exception hierarchy per module
Each subsystem defines its own exception type, which lets callers catch broadly or narrowly and keeps failure modes legible.

### ✅ Good — Pinned dependencies and a documented runtime baseline
Dependencies are version-pinned, and the container documents *why* it pins the Python version it does. Reproducibility by construction.

### ⚠️ Bad — Multiple disagreeing version strings for one artifact
The package version is stated in more than one place, and the places disagree. A reader cannot tell what version they are running.
🔧 **How to improve:** one source of truth for the version (e.g. read it from package metadata), referenced everywhere else.

### ⚠️ Bad — Framework-v1 idioms on a framework-v2 dependency
The code uses validation and serialization idioms that the installed major version has deprecated. It works today and will warn or break on the next upgrade.
🔧 **How to improve:** migrate to the current idioms while the deprecation is still a warning, not a breakage.

### ⚠️ Bad — Package-internal modules use path-dependent flat imports
Modules import their siblings as though they were top-level, so the package only resolves when its directory is on the path. This was accommodated at the config seam (a defensible, low-risk call for an import), but it means the package is not importable as a package and the process must start from a specific directory.
🔧 **How to improve (when the "don't rewrite" boundary lifts):** convert to package-relative imports so the package resolves the way its layout implies.

### ⚠️ Bad — Returning raw internal error text to the caller
A broad catch-all that places the underlying exception string into the response leaks internal detail and collapses precise, typed failures into a generic one.
🔧 **How to improve (general practice):** catch narrowly, log the detail server-side, and return a generic, non-revealing message to the caller.

### ⚠️ Bad — Mutating the same state from more than one layer
A piece of per-entity state is updated both inside a core routine and again by an outer caller for the same input, so it is advanced more than once per event. State should have exactly one owner.
🔧 **How to improve:** pick a single layer responsible for the mutation and remove the duplicate calls; add a test that pins the expected count after one input.

## 5. Testing Practices

### ✅ Good — Assertions test behavior, not just truthiness
The suite injects failing and rejecting collaborators and asserts the specific graceful-degradation and decision paths, rather than only checking that a call returns something. That is the difference between a test and a smoke check.

### ⚠️ Bad — Tests that pass because the fixture fabricates the answer
Some tests exercise the system with a mock that synthesizes whatever is asked of it, and assert that a value came back — which passes precisely *because* the mock always produces one. A green result there says the plumbing runs, not that the real behavior is correct. This is the classic "don't stub the seam you're trying to test" trap.
🔧 **How to improve:** test the real seam with a real (or realistic) implementation at least once, and reserve mocks for the collaborators you are *not* trying to verify. When a mock can never fail the assertion, the test is measuring the mock.

### ⚠️ Bad — Self-reported test counts that disagree across the repo
Different docs cite different numbers of tests, and none matches the tree. A drifting self-reported count is a small thing that quietly erodes trust in every other number in the docs.
🔧 **How to improve:** don't hand-maintain counts in prose; if a number must appear, generate it, or drop it and let the suite output be the source of truth.

### ⚠️ Bad — Test and quality tools declared but never run
Linters and type-checkers are listed as dependencies but there is no CI and nothing runs them.
🔧 **How to improve:** add a CI job that runs the suite plus lint and type checks on every push. A tool that is installed but never invoked provides none of its value.

## 6. Operational Practices

### ✅ Good — A hardened, self-explaining container
Non-root user, byte-code writes disabled, a real health check, and a single worker with a written explanation of *why* only one is safe. Operational decisions are documented at the point they are made.

### ⚠️ Bad — A health endpoint that always reports healthy
A liveness/readiness endpoint that returns a fixed "healthy" regardless of actual component state is a green light wired to nothing. A watchdog was added around the gap, but the endpoint itself should reflect reality.
🔧 **How to improve:** have the health check actually probe the components it claims are ready, so "healthy" means healthy.

### ⚠️ Bad — All state in process memory with no persistence
State lives in in-process structures, so a restart is a full wipe and the service is pinned to a single worker. Fine for a demo; a ceiling for anything more.
🔧 **How to improve:** put state behind a small interface now (even over the in-memory store), so a real backing store can be swapped in later without touching callers.

### ⚠️ Bad — Deprecated, timezone-naive timestamps throughout
Timestamps are produced with a deprecated call and carry no timezone, then subtracted directly in time-window math.
🔧 **How to improve:** use timezone-aware UTC timestamps consistently, so arithmetic across them is unambiguous.

---

*First review (v1.0), against `origin/main` at `2abde5a`. General engineering practices only — the product-specific security assessment, ratings, and cost analysis are maintained privately, as befits a live-intended cyber-detection product. All practices verified against a full read of the wired source, the six test files, the container/deploy config, and the superpowers specs. Companion (public): `agastya-development-pattern.md`.*
