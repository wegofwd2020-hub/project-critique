# P0 Implementation Tickets — ready to file as GitHub Issues

These are the implementation tickets that flow from the P0 documents created on 2026-06-11.
Each is written to be filed verbatim as a GitHub Issue (title · labels · body). Once the
GitHub connector is authenticated (run `/mcp`), I will file each in the listed repo.

Conventions for every ticket (WeGoFwd standards): Python; explicit exception handling
(no bare `except`, raise domain-specific errors); OpenSpec-compliant docstrings; every new
function ships with tests **and mock data**; no real child/student data in fixtures.

---

## Repo: `kathai-chithiram`

### KC-1 — Verifiable hard-delete of story, scene script, and media
**Labels:** `P0`, `privacy`, `compliance`
**Refs:** `PRIVACY.md` §5
**Why:** Parents must be able to delete a story and have *all* derived artifacts removed; this is the highest-risk privacy obligation.
**Acceptance criteria**
- A `delete_story(story_id)` operation hard-deletes raw story text, the derived scene script, and rendered media (and caches).
- Deletion cascades to backups on the next backup cycle (documented).
- No tombstoned copies of raw story text remain.
- Default retention job deletes undelivered story text after 30 days.
**Implementation notes**
- Add a deletion service with OpenSpec docstring; raise `StoryNotFoundError` / `DeletionError` explicitly.
- Test with mock stories asserting every artifact path is gone post-delete.

### KC-2 — Identifier minimization before LLM calls + provider no-training config
**Labels:** `P0`, `privacy`, `security`
**Refs:** `PRIVACY.md` §6
**Acceptance criteria**
- Child's real name is replaced with a token (`CHILD`) before any `wegofwd-llm` call and reinserted only at render time.
- No raw story text or real name written to plaintext logs.
- The provider config used (no-training / zero-retention) is recorded per request.
**Implementation notes**
- Pseudonymization util + test with mock story containing a name; assert outbound payload contains no name.

### KC-3 — Scene-script schema validation + safety gate before render
**Labels:** `P0`, `safety`
**Refs:** `docs/SCENE_SCRIPT_CONTRACT.md`, `docs/CONTENT_SAFETY.md` §5
**Acceptance criteria**
- A JSON Schema for scene-script v1 exists; every script is validated before rendering.
- Structural safety rules enforced (scene 2–8 s, caption matches narration, allowed transitions, `max_flash_hz ≤ 3`, banned-content flag).
- Invalid scripts are **rejected, not rendered**; failures logged without raw story text.
**Implementation notes**
- `validate_scene_script(script) -> None` raising `SceneScriptInvalidError` with the failing rule. Mock valid + invalid scripts in tests.

### KC-4 — Render-time seizure-safety guards + content-safety system prompt
**Labels:** `P0`, `safety`
**Refs:** `docs/CONTENT_SAFETY.md` §2/§3/§5
**Acceptance criteria**
- Renderers enforce frame-rate, no-flash (>3 Hz)/high-contrast oscillation limits, and audio-level caps.
- The generation system prompt encodes the MUST / MUST-NOT content rules.
- Human review gate remains until KC-3 + KC-4 are tested.

---

## Repo: `StudyBuddy_OnDemand` (compliance docs in `studybuddy-docs`)

### SB-1 — Verifiable parental consent (B2C) + school consent capture (B2B)
**Labels:** `P0`, `compliance`, `COPPA`, `FERPA`
**Refs:** `studybuddy-docs/compliance/COPPA_FERPA_COMPLIANCE.md` §2/§3
**Acceptance criteria**
- B2C signup cannot collect a child's PII until verifiable parental consent is captured and recorded.
- B2B (school-provisioned) path records the school's consent/authorization.
- Consent records are auditable (who/when/scope).
**Implementation notes**
- Extend auth flow; gate child data collection on a consent check. Tests with mock parent/school flows.

### SB-2 — Parent/school data review + delete + retention enforcement
**Labels:** `P0`, `compliance`, `privacy`
**Refs:** `COPPA_FERPA_COMPLIANCE.md` §2/§6, `PRIVACY_POLICY.md` §6
**Acceptance criteria**
- A parent (B2C) / school (B2B) can review and delete a student's data; deletion spans primary stores + next backup cycle.
- Retention policy enforced by a job; tested.
- Access to student records is audit-logged (FERPA).

### SB-3 — Children's privacy notice, subprocessor list, DPA process, LLM terms
**Labels:** `P0`, `compliance`, `legal`
**Refs:** `PRIVACY_POLICY.md`, `DPA_TEMPLATE.md`, `COPPA_FERPA_COMPLIANCE.md` §5/§6
**Acceptance criteria**
- Public children's privacy notice published; subprocessor list published and current.
- DPA executed with each school customer (template finalized by counsel).
- LLM provider no-training/zero-retention terms confirmed and documented.
- Counsel review completed before public launch.

---

## Repo: `pramana`

### PR-1 — DB-level REVOKE on audit table (app role cannot UPDATE/DELETE) + test
**Labels:** `P0`, `security`, `compliance`
**Refs:** `SECURITY.md` §3/§7
**Why:** The sister Thittam review left an `audit_log` REVOKE open; make it an acceptance test here so it never ships open.
**Acceptance criteria**
- Migration revokes UPDATE/DELETE on the audit table from the application role.
- An acceptance test asserts the app role cannot modify/delete audit rows.

### PR-2 — Append-only, tamper-evident audit log
**Labels:** `P0`, `security`, `compliance`
**Refs:** `SECURITY.md` §3/§4
**Acceptance criteria**
- Audit log is append-only; entries are attributable (who/what/when).
- Archive uses WORM/Object-Lock (e.g. S3 Object Lock) per resolved decisions.
- Tampering attempts are detectable; tested with mock audit events.

### PR-3 — SSO (SAML/OIDC) + RBAC with audited admin actions
**Labels:** `P0`, `security`
**Refs:** `SECURITY.md` §3/§4
**Acceptance criteria**
- SSO via SAML/OIDC; RBAC roles (employee, manager, compliance admin, auditor).
- Server-side authorization checks on every privileged action; admin/role changes audited.

### PR-4 — Injection-safe data layer + secrets + encryption verification
**Labels:** `P0`, `security`
**Refs:** `SECURITY.md` §3
**Acceptance criteria**
- All DB access parameterized (no string-built SQL); injection tests pass.
- Secrets sourced from a secret manager/env, never in source.
- Encryption in transit + at rest verified; errors never leak secrets/stack traces.

---

*After `/mcp` GitHub auth, these will be filed as issues in their respective repos with the labels above.*
