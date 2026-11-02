# ADR-004: Intermediate Timeline JSON Schema as Single Source of Truth

## Status
Accepted

## Context
In both Video Creation (Module A) and Video Editing (Module B), AI decisions (storyboards, cuts, zooms, reframing, volume ducking, captions) must be inspectable, human-editable, deterministic, and re-renderable.

If an AI script generator produces an opaque final video, the user cannot adjust a single scene or fix a caption typo without re-rendering the entire project from scratch.

## Decision
All AI pipelines compile into a single **Canonical Timeline JSON Schema** before rendering.
The timeline specifies:
- Canvas dimensions, aspect ratio, frame rate, audio sample rate, and target loudness (-14 LUFS).
- Multiple parallel tracks: `video`, `image`, `voice`, `music`, `sfx`, `captions`, `overlays`.
- Track clips with precise source in/out points, destination start/end timestamps, transitions, transforms (scale, pan, zoom, crop), and audio volume envelopes.
- Non-destructive edit decisions: decisions can be flagged `accepted`, `rejected`, or `modified` by the user in the UI/CLI.

## Rationale
- Decouples AI decision logic from FFmpeg rendering syntax.
- Enables non-destructive editing and human-in-the-loop checkpoints.
- Enables fast low-resolution proxy preview rendering and scene-level re-rendering (only re-rendering modified timeline segments).
- Guarantees schema validation via Pydantic v2.
