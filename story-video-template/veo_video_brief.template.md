# Veo 3.1 Video-Brief Template

The prompt template that turns a StoryUnit's `story.scenes` into a consistent,
reproducible video. It populates `video.brief` in `story_unit.schema.json`.

**Why a template and not free prompting:** consistency comes from holding the
*global* look + audio + references fixed and varying only the *per-shot* beat.
Re-describing the character every shot drifts; pinning it with an **ingredient**
(reference image) + a **seed** does not.

---

## 1. Global block — set ONCE per unit, identical for every shot

```
STYLE:    <one line look+mood>          e.g. "warm 2D storybook, soft flat color, rounded shapes, calm"
AUDIO:    <global narration/ambience>   e.g. "gentle female narrator, slow pace, soft room tone, no music"
NEGATIVE: <avoid everywhere>            e.g. "no flashing or strobing, no fast cuts, no on-screen text, no scary imagery, no photorealism"
SPEC:     model=veo-3.1  resolution=1080p  aspect=16:9  fps=24  audio=on  seed=<PIN>
```

> Pin `seed` the moment a unit reaches APPROVED so any re-render stays on-model.

## 2. Ingredients — up to 4 reference images (Veo 3.1 Ingredients-to-Video)

Lock identity/setting across shots. One row per recurring character or fixed set.

```
INGREDIENT[character:<id>]  ref=<image>  "child, ~6yo, blue shirt, short hair, friendly"
INGREDIENT[setting]         ref=<image>  "bright tidy bathroom, white tiles"
INGREDIENT[style]           ref=<image>  "reference frame for the storybook look"
```

## 3. Per-shot block — one per `story.scenes[]`, in order

Assemble each shot prompt in this fixed order (omit a slot only if irrelevant):

```
[scene_index] SUBJECT + ACTION + SETTING | SHOT_TYPE | CAMERA_MOVE | LIGHTING | DIALOGUE: "<spoken line>" | SFX: [..] | dur=<s> | NEG: <shot overrides>
```

Field guide:
- **SUBJECT/ACTION/SETTING** — from `scene.characters`, `scene.narration`, `scene.setting`. Refer to characters by their ingredient id so identity holds.
- **SHOT_TYPE** — `wide establishing` / `medium` / `close-up`.
- **CAMERA_MOVE** — `static` / `slow push-in` / `gentle pan`. Keep moves slow for calm audiences.
- **DIALOGUE** — usually equals `scene.narration`; this drives Veo's native synced audio.
- **dur** — `scene.duration_s`.

## 4. Worked example (kathai-chithiram, brushing-teeth social story)

```
STYLE:    warm 2D storybook, soft flat color, rounded shapes, calm
AUDIO:    gentle female narrator, slow pace, soft room tone, no music
NEGATIVE: no flashing, no fast cuts, no on-screen text, no scary imagery, no photorealism
SPEC:     model=veo-3.1 resolution=1080p aspect=16:9 fps=24 audio=on seed=4412

INGREDIENT[character:child] ref=child_ref.png "child ~6yo, blue shirt, short hair, calm smile"
INGREDIENT[setting]         ref=bathroom.png  "bright tidy bathroom, white tiles"

[1] child:child walks into the bathroom and looks at the sink | medium | static | soft morning light | DIALOGUE: "CHILD walks to the sink." | dur=4 | NEG: -
[2] child:child picks up the toothbrush, calm | close-up | slow push-in | soft morning light | DIALOGUE: "CHILD picks up the toothbrush." | SFX: [light tap] | dur=4
[3] child:child brushes teeth gently, smiling | medium | static | soft morning light | DIALOGUE: "CHILD brushes, up and down." | dur=5
```

> `CHILD` stays a pseudonymization token in stored artifacts; the real name is
> substituted only at render time (see `privacy` in the schema).

## 5. Worked example (pramana, SOX expense-approval lesson)

```
STYLE:    clean corporate explainer, flat illustration, neutral palette
AUDIO:    clear neutral narrator, professional, light ambient office tone
NEGATIVE: no on-screen text artifacts, no logos, no real faces
SPEC:     model=veo-3.1 resolution=1080p aspect=16:9 fps=24 audio=on seed=9071

INGREDIENT[character:approver] ref=approver.png "office manager at a desk, business casual"

[1] approver:approver reviews an expense report on a monitor | medium | slow push-in | even office light | DIALOGUE: "Every expense over the limit needs a second approver." | dur=6
[2] split screen showing submitter and approver, segregation of duties | wide | static | even office light | DIALOGUE: "The person who submits cannot be the person who approves." | dur=6
```

## 6. Generate-and-select workflow (how you actually get consistency)

1. Build the brief from `story.scenes` (one shot per scene).
2. Generate **3-4 takes per shot** (or per unit in Google Flow).
3. Human reviewer (`video.review`) picks the on-model take.
4. **Upscale** the chosen take to 1080p/4k (Veo upscaling) only after selection.
5. Record `seed` + the prompt build in `provenance[stage=video]`.
6. Stitch shots in scene order; store at `video.output.asset_ref`.

## 7. Provider note

`video.provider.id = "veo"` is the default verified generator. kathai may set
`"deterministic-renderer"` to keep its matplotlib/blender safety path while
reusing this same brief structure as the renderer's scene instructions. The
provider is resolved from the registry in the [`wegofwd-video`](../../wegofwd-video)
package (`wegofwd_video/registry.py`) — app code never hardcodes a model string,
exactly as `wegofwd-llm` does for text.
