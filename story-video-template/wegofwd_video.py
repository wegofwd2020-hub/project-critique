"""
wegofwd_video — reference provider registry for the Story->Video->Activities
template. Deliberately mirrors `wegofwd-llm/wegofwd_llm/registry.py`: logical
*roles* and provider ids map to a (provider, model) pair so model strings live in
ONE place with one update policy — app code never hardcodes a model id.

This is a SKETCH/contract to copy into a shared `wegofwd-video` library (the
natural third shared lib alongside wegofwd-llm + wegofwd-secure). It has no
vendor SDK wiring — only the registry, validation, and provenance surface that
both pramana and kathai-chithiram call.

BYOK throughout: callers pass their own key; the managed_env_key is the env var
for an optional managed key and is unused on the BYOK path.

Model ids marked UNVERIFIED are placeholders and MUST be validated against the
vendor before use. Veo 3.1 details verified against Google docs 2026-06-30
(720p/1080p/4k, native audio, Ingredients-to-Video) but NOT yet live-tested.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

VIDEO_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class VideoCapabilities:
    max_duration_s: int
    resolutions: tuple[str, ...] = ("720p",)
    aspect_ratios: tuple[str, ...] = ("16:9",)
    native_audio: bool = False
    reference_images: int = 0  # how many "ingredient" refs the model accepts
    upscaling: bool = False
    deterministic: bool = False  # True => same seed/script reproduces frames exactly


@dataclass(frozen=True)
class VideoProviderSpec:
    provider_id: str
    default_model: str
    capabilities: VideoCapabilities
    base_url: str | None = None  # None for SDK-native / local providers
    managed_env_key: str = ""
    model_verified: bool = False
    key_prefix: str = ""  # BYOK shape check; "" = length-only
    integration_version: int = 1


VIDEO_PROVIDER_REGISTRY: dict[str, VideoProviderSpec] = {
    "veo": VideoProviderSpec(
        provider_id="veo",
        # General OpenAI-incompatible Google video stack; reach via Vertex AI Veo
        # API or Google Flow. NOTE: the consumer Gemini app is the fast/720p tier
        # — point production at Vertex/Flow for 1080p/4k + Ingredients + seeds.
        base_url="https://aiplatform.googleapis.com",  # Vertex AI Veo endpoint family
        default_model="veo-3.1",
        capabilities=VideoCapabilities(
            max_duration_s=60,
            resolutions=("720p", "1080p", "4k"),
            aspect_ratios=("16:9", "9:16", "1:1"),
            native_audio=True,
            reference_images=4,  # Ingredients-to-Video
            upscaling=True,
        ),
        managed_env_key="VEO_API_KEY",
        model_verified=True,
    ),
    # kathai-chithiram's safety path: deterministic local render of the SAME brief.
    # No vendor, no key; reproducible frames for human-review gating.
    "deterministic-renderer": VideoProviderSpec(
        provider_id="deterministic-renderer",
        base_url=None,
        default_model="blender-grease-pencil-v2",
        capabilities=VideoCapabilities(
            max_duration_s=120,
            resolutions=("720p", "1080p"),
            native_audio=False,
            reference_images=0,
            deterministic=True,
        ),
        model_verified=True,
    ),
    "runway": VideoProviderSpec(
        provider_id="runway",
        base_url="https://api.dev.runwayml.com",  # UNVERIFIED
        default_model="gen-4.5",  # UNVERIFIED — best for granular camera control
        capabilities=VideoCapabilities(
            max_duration_s=20, resolutions=("720p", "1080p"), native_audio=True, reference_images=1
        ),
        managed_env_key="RUNWAY_API_KEY",
        key_prefix="key_",
    ),
    "kling": VideoProviderSpec(
        provider_id="kling",
        base_url="",  # UNVERIFIED
        default_model="kling-3.0",  # UNVERIFIED — 4k/60fps, multi-shot storyboard
        capabilities=VideoCapabilities(
            max_duration_s=15,
            resolutions=("720p", "1080p", "4k"),
            aspect_ratios=("16:9", "9:16"),
            native_audio=True,
            reference_images=1,
        ),
        managed_env_key="KLING_API_KEY",
    ),
}

# Logical role -> (provider_id, model). The seam both apps call. One place to
# route by cost/safety without touching call sites.
ROLE_DEFAULTS: dict[str, tuple[str, str]] = {
    "narrative-video": ("veo", "veo-3.1"),          # pramana lessons, kathai (once safety-cleared)
    "safety-render": ("deterministic-renderer", "blender-grease-pencil-v2"),  # kathai default today
    "fast-preview": ("veo", "veo-3.1"),             # generate cheap, upscale the keeper
}


class VideoConfigurationError(ValueError):
    """Unknown provider/role/model (maps to 422)."""


class VideoNotAllowedError(PermissionError):
    """Known provider excluded by the author's allow-list (maps to 403)."""


def available_providers(allowed: Iterable[str] | None = None) -> list[str]:
    ids = list(VIDEO_PROVIDER_REGISTRY)
    if allowed is None:
        return ids
    allowset = set(allowed)
    return [p for p in ids if p in allowset]


def validate_selection(
    provider_id: str,
    model: str | None = None,
    *,
    allowed: Iterable[str] | None = None,
) -> tuple[str, str]:
    """Resolve + validate a caller's video choice. Unknown -> VideoConfigurationError;
    excluded -> VideoNotAllowedError. Model accepted as-is (no vendor catalogue)."""
    spec = VIDEO_PROVIDER_REGISTRY.get(provider_id)
    if spec is None:
        raise VideoConfigurationError(f"unknown video provider {provider_id!r}")
    if allowed is not None and provider_id not in set(allowed):
        raise VideoNotAllowedError(f"provider {provider_id!r} excluded by allow-list")
    return provider_id, (model or spec.default_model)


def resolve_role(role: str) -> tuple[str, str]:
    try:
        return ROLE_DEFAULTS[role]
    except KeyError:
        raise VideoConfigurationError(f"unknown role {role!r}") from None


def provenance(provider_id: str, model: str | None = None, *, seed: int | None = None) -> dict:
    """Stampable record of WHICH video model + versions produced an asset — written
    into StoryUnit.provenance[stage=video] so stale/outdated renders are detectable.
    Mirrors wegofwd_llm.provenance()."""
    pid, chosen = validate_selection(provider_id, model)
    spec = VIDEO_PROVIDER_REGISTRY[pid]
    return {
        "stage": "video",
        "engine": "wegofwd-video",
        "provider": pid,
        "model": chosen,
        "model_verified": spec.model_verified,
        "integration_version": spec.integration_version,
        "contract_version": VIDEO_CONTRACT_VERSION,
        "seed": seed,
    }


def assert_brief_within_capabilities(provider_id: str, *, resolution: str, aspect: str,
                                     duration_s: float, ingredients: int) -> None:
    """Fail fast before dispatch if a brief asks for more than the provider supports
    (e.g. 4 ingredients to a model that takes 1, or 4k from a 1080p-max provider)."""
    spec = VIDEO_PROVIDER_REGISTRY[validate_selection(provider_id)[0]]
    caps = spec.capabilities
    problems = []
    if resolution not in caps.resolutions:
        problems.append(f"resolution {resolution} not in {caps.resolutions}")
    if aspect not in caps.aspect_ratios:
        problems.append(f"aspect {aspect} not in {caps.aspect_ratios}")
    if duration_s > caps.max_duration_s:
        problems.append(f"duration {duration_s}s > max {caps.max_duration_s}s")
    if ingredients > caps.reference_images:
        problems.append(f"{ingredients} ingredients > max {caps.reference_images}")
    if problems:
        raise VideoConfigurationError(f"{provider_id} cannot satisfy brief: " + "; ".join(problems))
