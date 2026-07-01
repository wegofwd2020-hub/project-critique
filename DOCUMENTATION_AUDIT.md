# WeGoFwd2020 — Documentation Audit

**Date:** 2026-06-11 · **Scope:** all 13 repositories · **Companion:** `PRODUCT_CATALOG.md`, `PORTFOLIO_SCORECARD.md`

This audit checks each project for the documents it *should* have for its stage and type, and flags what's missing. Headline: documentation tracks commercial maturity almost perfectly — the three serious bets (StudyBuddy, Thittam, Pramana) are richly documented; the prototype/passion projects have little to nothing.

---

## Coverage matrix

Legend: **Y** = present · **d** = present but lives in a `docs/` subfolder or companion repo · **–** = missing · **stub** = present but placeholder/incomplete

| Repo | README | LICENSE | CHANGELOG | CLAUDE.md | docs/ | ADRs | API/OpenSpec | Tests | .gitignore | Security/Privacy |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| StudyBuddy_OnDemand | Y | – | – | Y | Y (49) | ADR_001 only | Y | Y | partial |
| studybuddy-docs | Y | – | Y | – | Y (68) | – | Y | n/a | Y |
| Mentible | Y | Y | – | Y | Y | Y | – | Y | – |
| studybuddy_free | Y | Y | – | – | Y | – | – | Y | – |
| pramana | Y | – | – | – | Y (73) | as "decisions" | Y | Y | – |
| kathai-chithiram | Y | – | – | – | – | – | – | – | – |
| thittam | Y | Y | – | Y | Y (6) | – | d | Y | Y | d |
| thittam_docs | Y | – | – | Y | Y (96) | Y | Y | n/a | Y |
| dronePrjs | – | – | – | stub | – | – | – | Y | Y | – |
| MarketingTools | Y | – | – | – | – | – | – | – | Y | – |
| mambakkam-net | Y | Y | d | – | Y | – | – | Y | Y | Y |
| coding-standards | Y | – | – | – | n/a | n/a | n/a | n/a | – | n/a |
| project-critique | Y | – | – | – | n/a | n/a | n/a | n/a | – | n/a |

---

## Per-lineage assessment

### Engine lineage

**StudyBuddy (OnDemand + studybuddy-docs)** — the gold standard. Across both repos: architecture, backend architecture, requirements, UX requirements, domain model, event schemas, API reference, deployment, operations runbooks, observability, scalability, 18 epic docs, a glossary, a cost plan, a feature roadmap, and a full promo/sales set (VC deck, competitive landscape, security posture). *Gaps:* no `LICENSE` on the code repo; formal **ADRs are thin** (one ADR in code, none in the docs repo despite heavy "DESIGN_*" docs — decisions are documented, just not as numbered ADRs); **no dedicated privacy/COPPA-FERPA compliance document** even though the product serves minors (security posture exists; a child-data privacy policy + DPA does not appear to).

**Pramana** — excellent for a spec-phase project: initial analysis, resolved decisions, six regulatory framework references, an API spec area, and user-stories. *Gaps:* no `LICENSE` file despite the README declaring "Proprietary — All Rights Reserved"; no top-level `SECURITY.md`/threat model, which is notable for a *compliance* product; no `CLAUDE.md`; ADRs exist only as prose "resolved decisions," not numbered records.

**Mentible** — appropriate for pre-MVP: README, SCOPE, MVP doc, ADR folder, CLAUDE.md, LICENSE. *Gaps:* no tests yet (expected — no code), no BYOK privacy/security note despite handling user API keys.

**StudyBuddy Free** — shipped product with README, LICENSE (MIT), docs, tests. *Gaps:* no `CHANGELOG` (it's a versioned, shipped app — it should have one), no `.gitignore`, no `CLAUDE.md`.

**Kathai Chithiram** — **the biggest gap, and the most sensitive.** Only a README exists: no `docs/`, no `LICENSE`, no `CLAUDE.md`, no `.gitignore`, no tests, and — critically — **no privacy/data-handling or content-safety documentation** even though the product ingests *real, personal stories about real, vulnerable children* and produces media for them. It also has no written **scene-script contract**, which its own README says the architecture depends on.

**MarketingTools** — internal tool: README + .gitignore only. *Gaps:* no `CLAUDE.md`, no tests, no `LICENSE`; the brand rules live in `assets/brand/` but aren't documented as a usage/operations guide. Lighter bar (internal), but tests matter since it generates outbound copy.

### Anchor

**Thittam (thittam + thittam_docs)** — very strong, by design split: thin in-repo docs (6) with the depth in `thittam_docs` (96) — architecture, data model, deployment (K8s + CI/CD), security (RBAC, argon2id, impersonation, error handling), testing strategy, per-vertical guides, compliance/audit-trail, and CONTRIBUTING. The most complete doc set in the portfolio. *Gaps:* no `LICENSE` on the docs repo; no `CHANGELOG`; formal ADR coverage is lighter than the breadth of decisions implies.

### Passion

**dronePrjs** — `CLAUDE.md` is a **placeholder stub** (title typo "dronePrhs", literal "your frameworks here" / "the stuff you wish you'd known" prompts) and there's **no README at all**, no `docs/`, no `LICENSE`. For a robotics/drone project the absence of a **safety/operating-envelope doc** and the promised per-subproject (`closedSpace`/`openSpace`) domain docs is the notable gap. Tests and .gitignore exist.

### Supporting repos
`coding-standards` and `project-critique` are themselves documentation; they're fine as-is. Minor: neither has a LICENSE, which matters if `coding-standards` is meant to be reused/shared.

---

## Cross-cutting gaps (these recur across many repos)

1. **LICENSE files are missing almost everywhere** — absent from 9 of 13 repos, including products (`StudyBuddy_OnDemand`, `pramana`, `thittam_docs`). For the proprietary ones this should be an explicit copyright/all-rights-reserved file; for anything meant to be shared (`coding-standards`), an OSI license. Right now the legal status is ambiguous-by-omission.

2. **No privacy / data-protection documentation where it matters most** — StudyBuddy (minors → COPPA/FERPA) and Kathai Chithiram (children's personal stories) both process sensitive data about children and neither has a privacy policy, data-handling doc, or DPA. This is the highest-risk gap in the portfolio.

3. **CHANGELOGs are largely absent** — only `studybuddy-docs` and `mambakkam-net` have one. Shipped/late-build products (`studybuddy_free`, `StudyBuddy_OnDemand`, `thittam`) should each maintain one.

4. **ADR discipline is inconsistent** — `Mentible` and `thittam_docs` keep proper ADR folders; StudyBuddy's main docs, Pramana, and Thittam record decisions as prose design docs instead. Given how much you value decision records, a single ADR convention across the portfolio would pay off.

5. **OpenSpec/OpenAPI coverage is uneven** — you've stated a preference for OpenSpec-compliant docs; Pramana and StudyBuddy have API spec material, but it isn't a consistent, per-service artifact across Thittam's nine services or the StudyBuddy backend. (Worth a separate pass to confirm code-level docstrings meet your OpenSpec standard — this audit only covered document files.)

---

## Prioritized fix list

**P0 — do before any public launch or new build**
- **Kathai Chithiram:** add a privacy/data-handling doc (how parent stories and child data are stored, retained, deleted) and a content-safety guideline; add a `scene-script contract` spec; add `LICENSE`, `CLAUDE.md`, `.gitignore`.
- **StudyBuddy:** add a child-data **privacy policy + COPPA/FERPA compliance doc** (and DPA template) to `studybuddy-docs`; add a `LICENSE` to the code repo.
- **Pramana:** add the `LICENSE` file the README already implies, plus a `SECURITY.md`/threat model (table stakes for a compliance product).

**P1 — soon, supports the commercial bets**
- Add `CHANGELOG.md` to `studybuddy_free`, `StudyBuddy_OnDemand`, `thittam`.
- **dronePrjs:** write a real `README`, replace the placeholder `CLAUDE.md`, add a safety/operating-envelope doc and the per-subproject domain docs.
- Pick **one ADR convention** and backfill key decisions in StudyBuddy docs, Pramana, and Thittam.
- **MarketingTools:** add `CLAUDE.md` + tests (it generates outbound copy — regression-test the generators).

**P2 — when collaborators or open-sourcing appear**
- `CONTRIBUTING.md` for the active code repos (only `thittam_docs` has one).
- `LICENSE` for `coding-standards` if it's meant to be shared/reused.
- A portfolio-wide OpenSpec/OpenAPI consistency pass across services.

---

*This audit inspected document files and structure, not the substance of each doc. If useful, I can next verify code-level OpenSpec docstring compliance, or generate any of the P0 documents — the Kathai Chithiram privacy + scene-script contract is the highest-leverage place to start.*
