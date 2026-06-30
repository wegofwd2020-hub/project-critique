# Story → Video → Post-Activities — shared template

A stack-agnostic content template for the two portfolio apps that share the same
shape: **a story, an associated video, then post-activities.**

- **kathai-chithiram** — parent's story → calm captioned animation → engagement check-in (for special-needs children).
- **pramana** — SOX clause → compliance lesson video → scored quiz → certificate.

The two apps have very different stacks (pramana: FastAPI/Postgres/S3; kathai: a
minimal local library with strict privacy), so this is **not a shared code
library**. It is a **contract** each app implements against:

| File | What it is |
|------|------------|
| `story_unit.schema.json` | The data contract (JSON Schema 2020-12) for one unit: `story` + `video` + `activities` + `provenance` + `governance` + `privacy`. |
| `veo_video_brief.template.md` | The Veo 3.1 prompt template — turns `story.scenes` into a consistent, reproducible video brief. |
| `wegofwd_video.py` | **Pointer only** — the provider registry it sketched is now the real [`wegofwd-video`](../../wegofwd-video) library ([ADR-026](../../StudyBuddy_SelfLearner/docs/adr/ADR-026-shared-video-generation-library.md)), the third member of the `wegofwd-*` family (alongside `wegofwd-llm` + `wegofwd-secure`). |
| `example.kathai.json` / `example.pramana.json` | Worked units proving the one contract fits both apps. |

## The pipeline

```
STORY                 VIDEO                       POST-ACTIVITIES
parent text /         story.scenes ──► brief ──►  quiz (pramana, scored→cert)
clause ref     ──►    Veo 3.1 / renderer    ──►   feedback-checkin (kathai, primitives)
(wegofwd-llm)         (wegofwd-video)             (wegofwd-llm + app rules)
```

Each stage is generated/rendered **independently**, carries its **own
provenance**, and passes the app's **governance gate** before the next stage is
trusted. `story.scenes[]` is the spine: each scene becomes one `video.brief.shots[]`
and can anchor one comprehension item in an activity (`scene_index`).

## Design decisions (why it's shaped this way)

1. **Mirror `wegofwd-llm`.** Video gets the same `registry → role → provider →
   provenance` pattern that text already uses. App code never hardcodes
   `veo-3.1`; it asks for a role (`narrative-video`) and the registry resolves it.
   This keeps the portfolio's "one update policy for model ids" property.
2. **Pluggable provider, including a non-AI one.** kathai keeps its
   deterministic matplotlib/blender path (`provider.id = "deterministic-renderer"`)
   for safety while reusing the *same* brief structure. AI generation
   (`"veo"`) is opt-in per unit. No rewrite of kathai's render contract.
3. **Polymorphic activities.** One `activities[]` array, discriminated by `type`,
   covers pramana's scored `quiz` (pass threshold, certificate gating, cooldown)
   and kathai's unscored `feedback-checkin` (M1 primitives: `prompt_level`,
   `mood_checkin`, `completed`, keyed to `goal_id`). New apps add new types.
4. **Provenance is per-stage and honest.** `model_verified` rides through from the
   registry (Veo 3.1 is docs-verified, not yet live-tested — flagged truthfully,
   same convention as the LLM registry).
5. **Privacy is first-class.** The `privacy` block makes kathai's gates part of
   the contract: pseudonymization tokens never persist real names, and dispatch
   is refused unless `no_training` AND `zero_retention` hold.

## Adoption — pramana

- Persist a unit in **`ContentDraft.body`** (already JSONB `{modules, quiz, assets, artifacts}`); add `video` + `activities` (or map `quiz`→`activities[type=quiz]`).
- New service **`pramana/services/video_generation.py`** — call a `wegofwd-video` provider, write the S3 key to **`CourseVersion.video_asset_id`** at publish.
- Extend **`pramana/domain/publication.py`** with `materialize_video()` / `materialize_activities()` alongside `materialize_quiz()` (pure functions).
- Reuse the existing **approval state machine** (`governance.workflow = approval-state-machine`) and **audit** every stage via `services/audit.py`.
- `min_watch_pct` already exists for watch-gating before the quiz.

## Adoption — kathai-chithiram

- Write **`story_unit.json`** alongside the existing `scene_script.json` per story dir (the `scenes` here are the same beats — `scene_script` can be derived from / kept in sync with `story.scenes`).
- Keep **`deterministic-renderer`** as the default provider; the brief doubles as renderer scene instructions. Flip a unit to `"veo"` only once content-safety for AI video is proven (CONTENT_SAFETY.md §6) and the human-review gate passes.
- Add an **activities schema check** mirroring `scene_script/validation.py`; store engagement primitives minimized (privacy).
- The **`privacy`** block maps directly onto the existing `run_generation()` gates (pseudonymization, no_training/zero_retention, residual-identifier hard stop).

## Status / open items

- `wegofwd_video.py` has been **promoted** to the standalone [`wegofwd-video`](../../wegofwd-video) package (ADR-026); the file here is now just a pointer. Change the package, not this sketch, to avoid cross-repo drift.
- **Veo 3.1**: base_url/model/capabilities verified against Google docs 2026-06-30; `model_verified=True` follows the LLM-registry convention (docs-verified) but it is **not yet live-tested** from our stack. Flip to live-tested after a first real generation.
- `runway` / `kling` specs are **UNVERIFIED** placeholders, mirroring the LLM registry's honesty convention.
- Validate examples with `jsonschema` once a venv is available (`pip install jsonschema`; both examples are well-formed JSON and structured to the schema).
