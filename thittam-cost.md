# Thittam — Real-World Cost Analysis

**Analysed:** 2026-05-24 (v1.0 — first cost pass against HEAD `ce64378`; last real-code commit `2026-05-13`)
**Repo:** `wegofwd2020-hub/thittam` (sibling `thittam_docs` not checked out locally — docs not measured)
**Question being answered:** if this same artifact had been built by a conventional team in the real world (not by a single founder with Claude-assisted execution), what would it have cost in money and calendar time?
**Scope of measurement:** Go services + Web + Proto + SQL migrations + k8s/Istio/Kong infra + chaos engineering YAMLs + k6 load tests on disk at HEAD `ce64378`. "Late-build / pre-production on core services" state per the v1.3 critique. Production launch costs (financial-controls audit, security audit, datacentre, on-call rota, ledger reconciliation tooling) are **not** in either column.

---

## 1. What's actually been built

Measured directly from the repository (HEAD `ce64378`, 2026-05-24 bot commit; **last real-code commit 2026-05-13**; first commit 2026-04-03 → **~41 days of real-code activity**).

| Slice | Measure |
|---|---|
| **Go production LOC** | **~61,665** (87,886 total − 26,221 test) |
| Go test LOC / functions | 26,221 / **1,203 test functions** |
| Proto (gRPC schema) | **1,715 LOC** across **10 services**, **231 messages**, **123 RPC methods** |
| SQL migrations | **80 files / 2,076 LOC** |
| Microservice binaries (`cmd/`) | **13** (10 domain services + `thittam-cli` + `retention-sweeper` + `migrate-all-tenants`) |
| Shared `pkg/` packages | **22** (registration saga, audit, auth, tenantdb, secrets/Vault, jetstream, observability, ratelimit, vertical plugin system, …) |
| Web (Next.js + shadcn/ui) | **28,363 LOC** across **136 TS/TSX**; **29 App Router pages**; **4 Playwright specs** |
| Service-mesh / platform | **25 k8s YAMLs** (Istio destination rules, Kong per-service rate-limits, NetworkPolicies, ConfigMaps) |
| Operability | **6 Prometheus alert files** (SLO, billing, NATS, nats-DLQ, retention-sweeper, infra) |
| Chaos engineering | **3 chaos YAMLs** (postgres-replica-lag, nats-partition, ledger-503) wired into a `chaos-ledger-503.js` k6 scenario |
| Load testing | **7 k6 scenarios** (ledger-throughput, expense-submissions, budget-approvals, lb-distribution, report-under-load, chaos-ledger-503, full-suite) |
| Multi-tenancy | **tenant-per-schema** (harder than RLS), with `migrate-all-tenants` orchestrator |
| Compliance posture | T1 secret handling via Vault, schema-injection-resistant tenant routing (verified on disk); **`audit_log` REVOKE remains the one open P0** |
| Verticals | Vertical Plugin System; 2 demo tenants seeded (XYZ_CBA movie production INR, XYZ Construction USD) |
| Activity | **192 commits**, **132 issue-referencing**, sole-author |
| **Production LOC (Go + Web + Proto + SQL + YAML, excl. tests)** | **~94,000 LOC** |

**Why this matters for cost:** Thittam has *less* LOC than a comparable monolith would have, but materially *more architectural surface area* — 10 gRPC microservices, NATS JetStream event bus with DLQ, k8s + Istio + Kong service mesh, chaos engineering wired to k6 load tests, tenant-per-schema, the buf+sqlc strict toolchain, financial-domain correctness on the ledger. **Distributed systems work has a well-established 1.5–2× productivity penalty per LOC vs. monolith work.** That penalty shows up in both team composition (you can't safely staff this with juniors) and elapsed time.

---

## 2. Methodology — triangulated three ways

A single estimate from one method is not defensible. I used three independent methods and reported the convergence.

1. **Industry-velocity benchmark.** A 10-microservice financial/ERP SaaS with multi-tenancy + service mesh + chaos engineering + load tests, reaching "late-build / pre-production": **40–60 engineer-months** in a competent team. Reference points: post-mortems from B2B fintech / ERP startups, distributed-systems case studies, observed velocity at companies with comparable service-count and operability posture.
2. **COCOMO-II modernized.** ~94 KLOC × normal coefficients × 0.3 modern-tooling multiplier (smaller than a monolith's 0.25 because microservices give back the productivity that frameworks add) ≈ **~95 EM**. Treated as the upper sanity bound.
3. **Feature / service counting.** 10 services × ~5 weeks/service for a team of 3–4 backend + 2 weeks/service of cross-cutting platform work = **52–60 EM**.

**Convergence: 40–60 engineer-months is the defensible range.** Point estimate **48 EM**.

---

## 3. Team composition

Assume **48 EM spread across 5.5 FTE for ~10.9 calendar months**. The 5.5 FTE is driven by needing a **dedicated platform/SRE engineer** — k8s + Istio + Kong + Prometheus + NATS + chaos engineering is a real full-time job, not a fractional role.

| Role | FTE | Why this is non-negotiable for Thittam |
|---|---|---|
| Staff/Architect (distributed systems) | 1.0 | gRPC + sqlc + tenant-per-schema + event-sourcing decisions are unforgiving |
| Senior Backend Engineer (Go) | 2.0 | 10 services + 22 pkg shared libs needs more than 1 senior |
| Senior Frontend Engineer | 1.0 | Next.js + shadcn/ui + grpc-gateway REST shadow integration |
| Platform / SRE | 1.0 | **Full-time**, not 0.5 — service mesh + observability + chaos |
| Product Designer | 0.5 | Less UI surface than a typical SaaS (4 specs vs. ~17 in comparable monoliths) |
| Product Manager | 0.5 | Vertical plugin system + multi-tenant demo orchestration |
| QA / SDET | 0.5 | 1,203 tests + 7 k6 scenarios + 3 chaos YAMLs |
| **Total** | **5.5 FTE** | |
| External: financial-controls / compliance counsel | as-needed | Depending on regulated-geography rollout |

---

## 4. Cost scenarios

### Scenario A — US tech labour market (Bay Area / NYC / Seattle blended, 2025–2026 rates)

| Role | FTE | Loaded $/yr | 10.9-mo cost |
|---|---|---|---|
| Staff/Architect | 1.0 | $480k | $436k |
| Sr Backend × 2 | 2.0 | $330k each | $599k |
| Sr Frontend | 1.0 | $320k | $291k |
| Platform / SRE | 1.0 | $350k | $318k |
| Designer | 0.5 | $260k | $118k |
| PM | 0.5 | $300k | $136k |
| QA / SDET | 0.5 | $220k | $100k |
| **People subtotal** | **5.5** | | **$1,998k** |
| Financial compliance counsel + retainer | | | $40k |
| Infra (AWS EKS, Datadog, NATS managed, Vault, pgbouncer, Postgres HA) | | | $80k |
| Tooling & SaaS (GitHub Enterprise, Linear, Figma, Buf Schema Registry, sqlc, observability) | | | $35k |
| Equipment + onboarding amortization (5.5 hires × ~$8k) | | | $44k |
| **Scenario A total** | | | **~$2.20M** |

### Scenario B — Blended global / India tier-1 + EU senior contractors

| Role | FTE | Loaded $/yr | 10.9-mo cost |
|---|---|---|---|
| Staff/Architect | 1.0 | $150k | $136k |
| Sr Backend × 2 | 2.0 | $90k each | $164k |
| Sr Frontend | 1.0 | $85k | $77k |
| Platform / SRE | 1.0 | $95k | $86k |
| Designer | 0.5 | $70k | $32k |
| PM | 0.5 | $95k | $43k |
| QA / SDET | 0.5 | $55k | $25k |
| **People subtotal** | **5.5** | | **$563k** |
| Compliance counsel (still US/EU) | | | $30k |
| Infra (Hetzner / DO / Linode k8s + self-hosted observability) | | | $55k |
| Tooling & SaaS | | | $30k |
| Equipment + onboarding | | | $33k |
| **Scenario B total** | | | **~$711k** |

### Scenario C — Junior-heavy lean team

**Not recommended.** A 10-microservice financial system with ledger correctness invariants, service mesh, and chaos-engineered failure modes cannot be safely staffed with mid-level-and-below engineers. The most likely outcome is a 14–18 month schedule with a v0 that fails the chaos tests on the first real-world incident.

If forced: 1 senior lead + 4 mid Go engineers ≈ **~$580k** over 14 months at blended rates — but with material correctness risk that no spreadsheet captures.

---

## 5. Calendar-time cost

| Scenario | Wall-clock duration to reach `ce64378` equivalent |
|---|---|
| US team, 5.5 FTE | **10–12 months** |
| Blended global team, 5.5 FTE | **11–13 months** |
| Junior-heavy lean team | **14–18 months**, with correctness risk |
| **Actual (single founder + Claude Opus 4.x)** | **~41 days** (6 weeks) of real-code commits |

---

## 6. What was actually spent

| Line item | Estimate |
|---|---|
| Founder time, ~41 days × ~10h/day focused | ~410 hours |
| Claude Code subscription / API (intensive 6 weeks) | $300–1,500 |
| Hetzner VM + Postgres + bandwidth (dev/demo) | ~$100 |
| Vault dev, NATS local, k8s local (no managed services) | ~$50 |
| Domain + miscellaneous services | ~$100 |
| **Direct cash outlay** | **~$0.6k–$2k** |
| Founder opportunity cost @ $300k/yr × 41 days | **~$34k** |
| **All-in actual cost** | **~$34k–$36k** |

---

## 7. Headline ratios

| Comparison | US scenario | Blended scenario |
|---|---|---|
| Cash-only multiplier | **~1,100× cheaper** ($2.20M ÷ $2k) | **~355× cheaper** ($711k ÷ $2k) |
| All-in multiplier (incl. founder opp-cost) | **~61× cheaper** ($2.20M ÷ $36k) | **~20× cheaper** ($711k ÷ $36k) |
| Calendar compression | **~7.5× faster** (41 days vs. ~11 months) | **~8× faster** (41 days vs. ~12 months) |
| Team-size compression | **5.5× smaller** (1 vs. 5.5 FTE) | **5.5× smaller** |

---

## 8. Honest caveats

- The 48 EM estimate assumes a competent team. A sloppy team would burn substantially more (microservices punish poor design more than monoliths do); an elite distributed-systems team could probably hit 40 EM. Range **40–60 EM** is defensible.
- The "71 docs / 13 ADRs" claim from the v1.3 critique is **still unverifiable** here — `thittam_docs` is a sibling repo not checked out locally. If those exist as claimed, add **~$15–30k** of technical-writing / architecture-documentation cost to the US scenario.
- **Ledger correctness is the load-bearing risk** that distinguishes Thittam from typical SaaS. Both the conventional team and the founder still need an external accounting / audit review before charging real customers; that's **~$30–80k either way** and is **not in any column** above.
- **Tenant-per-schema** is harder to operate past ~500 tenants. The critique flagged this as an unaddressed scalability question. A real team would burn ~2–4 EM on a sharding / migration plan before launch; the founder hasn't yet, but neither has anyone else in either scenario.
- **Chaos engineering being scaffolded** (3 chaos YAMLs + k6 chaos scenario) is unusual for a 41-day build. It's worth ~1–2 EM of platform-engineering effort in the conventional model — already counted in the SRE 1.0 FTE.
- The actual build benefits from a senior-architect-level founder making structural calls. A less-experienced founder + Claude would not hit this velocity for a 10-microservice financial system even with the same tooling. **More of the multiplier here is the founder than in a monolith comparison**, because architectural decisions compound across services.
- Equity is excluded from all cash columns. A real team's *total* compensation including equity at face value would be ~30% higher than the loaded-cost figures above.

---

## 9. What this means

The cash-only ratios (1,100× / 355×) are headline-grabbing but somewhat misleading — they ignore that the founder is paying themselves in time, not cash. The **all-in multipliers (61× US / 20× blended)** are the honest comparison and are still striking.

The Thittam ratios are *higher* than the equivalent monolith ratios because:

1. **The conventional baseline is higher.** Distributed systems work is genuinely expensive to staff correctly — you cannot economize the platform engineer or the architect.
2. **The actual cost is similar to a monolith.** AI assistance doesn't get materially more expensive when generating gRPC services vs. REST routes; the founder's marginal hour is the constraint.

The more durable observation is the **calendar compression**: a single founder reached a "late-build / pre-production" state in 6 weeks that a 5.5-FTE conventional team would need ~11 months to reach. In a B2B SaaS competitive market that 9+ month head-start is worth far more than the dollar savings — it's the difference between being a category contender and being a follower.

The artifact has 1,203 tests, chaos engineering, load tests, formal proto definitions across 10 services, multi-tenant correctness verified on disk, and a documented saga for the registration pipeline. This is not a "demo-quality" comparison. It is a real artifact compared against what a real team would have built.

---

*Cost analysis is a point-in-time exercise. Loaded rates, market conditions, and AI tooling capability all evolve. Re-run this analysis annually if it's being used to inform staffing or fundraising decisions.*
