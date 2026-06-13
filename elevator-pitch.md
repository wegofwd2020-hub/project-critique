# Elevator Pitch — Sivakumar (Siva) Mambakkam

**Audience:** Employers & Consulting Clients  
**Author:** Sivakumar (Siva) Mambakkam  
**Date:** 2026-06-13 (v1.2 — refreshed after the shared `wegofwd-llm` LLM-seam extraction proved the *one IP, many products* claim; refresh adds cost-evidence numbers and consolidates the rule count to 21)  
**Prior:** April 2026 (v1.1 — post StudyBuddy Epic 10/11 + Thittam proto completion)  
**Contact:** siva.mambakkam@gmail.com | linkedin.com/in/sivamambakkam | +1 (734) 560-0202

---

## The 30-Second Hallway Version

"I'm Siva Mambakkam — Enterprise Architect, 30 years. Ford autonomous vehicles, GM
infotainment, GE Aerospace, UWM at mortgage scale.

Since 2025 I've been doing something unusual for an architect — I took two domain
problems I couldn't find good solutions for in the market, wrote the problem statements
myself, and built both platforms to production quality from the ground up. One is an
AI-powered K-12 tutoring SaaS with FERPA compliance baked into the database layer. The
other is a multi-tenant production management platform with a real double-entry general
ledger, serving four different industries from one codebase.

The architecture pattern under both — a scoped query against a shared, provider-agnostic
LLM seam — is now a published Python library (`wegofwd-llm`) load-bearing across the
family. The two products aren't disconnected demos; they're applications of one
defensible IP, with measured execution velocity to match — independent cost analysis puts
the build at roughly 28× cheaper than a conventional team would have spent.

I did that because I believe the best architects don't just draw boxes — they own the
problem. That's what I bring to a team."

---

## The Interview Opener — 3 Minutes

"My background is 30 years of enterprise architecture across some demanding environments
— autonomous vehicle platforms at Ford, infotainment and telematics at GM, integration
architecture at GE Aerospace, and most recently DevOps and platform architecture at
United Wholesale Mortgage, where scale and regulatory precision are non-negotiable.

What ties all of that together is a consistent pattern: I come in where the business
problem is real but the technical path is unclear, and I build the bridge between them.
At Ford that meant defining how cloud services talk to a vehicle. At UWM that meant
turning raw telemetry into KPIs that executives could use to make capital allocation
decisions.

Since 2025 I've taken that same discipline and applied it to two products I
conceived from scratch. Not side projects — production-grade platforms with documented
architecture decisions, codified engineering standards, compliance controls, and test
suites. One is a K-12 STEM tutoring SaaS where the AI content pipeline is completely
separated from the student-facing API — so no student ever holds an API key, costs are
operator-controlled, and the system is COPPA and FERPA compliant by design, not by
policy. The other is a multi-industry production management SaaS with a double-entry
general ledger and a plugin architecture that serves film production, construction,
software teams, and event management from a single codebase — because the financial
model underneath is identical, only the vocabulary changes.

What proves the *shared-IP* claim isn't an assertion — it's the fact that the
multi-provider LLM seam underneath both is now its own published library (`wegofwd-llm`,
ADR-012): a typed contract, registry, and validate→repair conformance loop, BYOK by
construction, no key ever in an exception or a log line. It was extracted from one
product and re-injected into the other — same code, two consumers, with three-axis
versioning so a generated artefact records which seam produced it. That extraction is
the moment "one IP, many products" stopped being a story I told and became a
package on disk.

Building those taught me something I couldn't have learned purely from enterprise
engagements: what it costs to make the wrong architectural call early, and how to design
standards that hold up when you're the one who has to live with them. I wrote 21
non-negotiable engineering rules before writing a line of application code (started at
18, grew as new patterns earned formalization) — and every platform in the family still
conforms to every one of them. When two of those rules turned out to contradict each
other on secret handling, I resolved the contradiction by revising the rule and
migrating both codebases to match — not by patching around it.

That combination — enterprise-scale experience, domain breadth, and the founder's
mindset of owning a problem end to end — is what I bring to a team or a client
engagement."

---

## The Consulting Proposal Version

*For a first email, a LinkedIn note, or an intro meeting.*

---

**Subject: Enterprise Architect — 30 years, two production SaaS platforms, available
for engagements**

I'm Siva Mambakkam, an Enterprise Architect with 30 years across Ford, GM, GE Aerospace,
and United Wholesale Mortgage. My work has spanned autonomous vehicle platforms,
connected commerce, enterprise integration, MLOps at scale, and API governance for
regulated financial services.

I am currently available for architecture consulting and advisory engagements.

What distinguishes my approach is that I don't deliver architecture documents and walk
away. Since 2025 I have designed and built two production-grade SaaS platforms
from problem statement to working software:

**StudyBuddy OnDemand** — A COPPA and FERPA-compliant K-12 AI tutoring platform where
AI content is pre-generated at the operator level, schools subscribe as the primary
billing entity, and database-enforced row-level security provides tenant isolation that
satisfies a security audit without relying on application-layer correctness.

**Thittam** — A multi-tenant production management SaaS with a double-entry general
ledger, budget approval workflows, and an industry plugin system that serves film
production, construction, software development, and events management from a single Go
microservices codebase — because the financial model is identical across all four; only
the vocabulary differs.

Both platforms are built to the same standards I apply in enterprise engagements:
documented Architecture Decision Records, event-driven design, API-first contracts,
structured observability from day one, and codified engineering rules that a team can be
held accountable to. The cross-cutting LLM-provider seam was extracted into a published
Python library (`wegofwd-llm`) once it had earned reuse — three on-disk consumers,
typed contract, BYOK by construction, no key ever in an exception or log. Independent
cost analysis of the K-12 platform alone puts the build at ~28× cheaper than a
conventional team would have spent — receipts, not assertions.

I engage at the level where architecture and business strategy meet — defining what to
build, why, and in what order — and I am equally comfortable in the room with
engineering teams validating implementation decisions.

If you have a platform modernisation, a greenfield build, or an architecture governance
challenge, I'd welcome a conversation.

---

## One Line — LinkedIn Headline / Email Signature

> Enterprise Architect — 30 years across Ford, GM, GE and banking | Author of two
> production-grade SaaS platforms | Available for architecture consulting and advisory
> engagements

---

## Why This Pitch Works for This Audience

Employers and consulting clients are screening for three things. Here is how your story
answers each one.

| Their Question | Your Answer |
|---|---|
| "Can they handle complexity and ambiguity?" | Ford autonomous vehicles, GE Aerospace integration, UWM at mortgage scale — all regulated, all complex |
| "Do they just draw diagrams or do they own outcomes?" | Conceived two products, wrote the problem statements, built them to production quality — no team, no budget, no excuses. Independent cost analysis: ~28× cheaper than a conventional team for the K-12 platform |
| "Will they raise our standards or just fit in?" | 21 non-negotiable engineering rules written before a line of code (loaded into every Claude Code session, applied uniformly across the family). ADRs. Separate docs repos. FERPA in the database layer, not the application layer |
| "Have they actually built reusable infrastructure?" | The cross-product LLM seam is a published library (`wegofwd-llm`, ADR-012) with three on-disk consumers, three-axis versioning, and BYOK enforced at construction — extracted from one product, re-injected into another |

The two products are not a distraction from your enterprise credentials — they are the
proof that your credentials are real.

---

## Credential Anchors

Reference these when the conversation goes deeper.

| Claim | Evidence |
|---|---|
| Regulatory environments | UWM (mortgage / financial services), BCBSM (healthcare) |
| Autonomous & connected systems | Ford (autonomous vehicle platforms, cloud-to-vehicle deployment), GM (infotainment & telematics) |
| Enterprise integration at scale | GE Aerospace (MQ-based messaging), Ford (vehicle integration standards) |
| AI-native product design | StudyBuddy OnDemand — three-context separation; Anthropic API key never reaches a student device |
| Multi-tenant SaaS architecture | Thittam — tenant-per-schema PostgreSQL, gRPC microservices, NATS JetStream, Istio mTLS |
| Compliance by design | COPPA, FERPA enforced at the database layer via PostgreSQL Row-Level Security |
| Standards and governance | 21 codified engineering rules applied across the family (loaded into every Claude Code session via a shared standards repo); 30+ ADRs across the portfolio; doc-drift CI enforcement |
| Shared infrastructure (proven) | `wegofwd-llm` — published Python library (BYOK, schema-agnostic, three-axis versioning); three on-disk consumers across StudyBuddy_OnDemand, SelfLearner/Mentible, Kathai Chithiram |
| Execution velocity (measured) | Independent cost analyses (`project-critique/*-cost.md`): ~28× cheaper US / 9× blended for StudyBuddy OnDemand vs a conventional team; comparable ratios for Thittam, SelfLearner, MarketingTools |
| Cloud breadth | AWS Certified Solutions Architect; Google Cloud Infrastructure; Azure APIM governance at UWM |
