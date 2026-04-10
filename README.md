# Project Critique — WeGoFwd2020

Code review and architectural critique for StudyBuddy OnDemand and Thittam.

**Reviewed:** April 2026  
**Reviewer:** Claude (Anthropic)  
**Scope:** Architecture, code quality, test coverage, documentation, security, scalability

---

## Contents

| File | Project | Description |
|---|---|---|
| [studybuddy-critique.md](studybuddy-critique.md) | StudyBuddy OnDemand | Code review — architecture, quality, security, scalability |
| [thittam-critique.md](thittam-critique.md) | Thittam | Code review — architecture, quality, security, scalability |
| [studybuddy-development-pattern.md](studybuddy-development-pattern.md) | StudyBuddy OnDemand | Full lifecycle analysis — scoping, design, architecture, development |
| [thittam-development-pattern.md](thittam-development-pattern.md) | Thittam | Full lifecycle analysis — scoping, design, architecture, development |
| [studybuddy-practices.md](studybuddy-practices.md) | StudyBuddy OnDemand | Good practices, bad practices, and how to improve |
| [thittam-practices.md](thittam-practices.md) | Thittam | Good practices, bad practices, and how to improve |

---

## Quick Summary

### StudyBuddy OnDemand

**Overall:** Strong foundations with a few critical gaps to close before launch.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟡 Good | Two frontends (Kivy + Next.js) unresolved; filesystem content store blocks horizontal scale |
| Code Quality | 🟡 Good | Stripe calls sync in async router; JWKS cache has no TTL enforcement |
| Test Coverage | 🟠 Fair | 70% threshold too low for children's SaaS; no E2E tests |
| Documentation | 🟢 Strong | Comprehensive docs repo; excellent module docstrings |
| Security | 🟡 Good | No visible rate limiting; dev router gating could be bypassed |
| Scalability | 🟡 Good | Content store must move to S3 before multi-host deployment |

**Top 3 actions:** (1) Move content store to S3, (2) Wrap Stripe calls in `run_in_executor`, (3) Enforce JWKS TTL.

---

### Thittam

**Overall:** Sophisticated architecture with ambition ahead of execution at mid-build stage.

| Area | Rating | Key Finding |
|---|---|---|
| Architecture | 🟡 Good | 4 of 9 proto definitions pending; 9 microservices may be premature |
| Code Quality | 🟢 Strong | 17 coding rules are excellent; T1 secret handling contradicts security docs |
| Test Coverage | 🟠 Fair | ~306 tests is low for a financial platform; no chaos testing |
| Documentation | 🟢 Strong | Best-in-class; 41+ files, 9 ADRs, 11 required diagrams |
| Security | 🟡 Good | Schema injection risk in tenant routing; impersonation lifecycle undefined |
| Scalability | 🟡 Good | Tenant-per-schema bottlenecks at 500+ tenants; reporting fan-out unresolved |

**Top 3 actions:** (1) Define pending protos for IAM/Ledger, (2) Validate tenant ID before `SET search_path`, (3) Design saga pattern for registration pipeline.

---

## How to Create This as a GitHub Repository

```bash
# 1. Create a new private repo at github.com/wegofwd2020-hub/project-critique
#    (via GitHub web UI or GitHub CLI)

# 2. Clone and add files
git clone https://github.com/wegofwd2020-hub/project-critique.git
cd project-critique

# Add the critique files (downloaded from this session)
cp studybuddy-critique.md .
cp thittam-critique.md .
cp README.md .

git add .
git commit -m "docs: initial code review — StudyBuddy OnDemand + Thittam (April 2026)"
git push origin main
```

---

*This critique is a point-in-time review based on publicly accessible code (StudyBuddy) and documentation (both projects) as of April 2026. The Thittam application code was not directly accessible (private repository); code-level observations are inferred from documentation and architectural descriptions.*
