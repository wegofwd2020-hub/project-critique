"""
wegofwd_video.py — PROMOTED. This sketch is no longer the source of truth.

The provider registry / contract / provenance seam this file originally sketched
has been promoted to a real standalone library:

    ../../wegofwd-video/            (the wegofwd-video package, ADR-026)
        wegofwd_video/registry.py   <- the registry, roles, build_provider, provenance
        wegofwd_video/contract.py   <- VideoBrief/Shot/Ingredient, VideoRequest/Result, VideoProvider
        wegofwd_video/providers/    <- veo (Veo 3.1) + deterministic-renderer

Decision record: StudyBuddy_SelfLearner/docs/adr/ADR-026-shared-video-generation-library.md

This file is kept only as a breadcrumb so links into the template still resolve.
Do NOT edit logic here — change the package instead, to avoid the cross-repo
drift the ADRs warn against. Consumers install the package, they do not copy this:

    pip install wegofwd-video @ git+<repo-url>@vX.Y.Z

The Veo prompt-building format lives in veo_video_brief.template.md; the StoryUnit
data contract lives in story_unit.schema.json (both in this directory).
"""
