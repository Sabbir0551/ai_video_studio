# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - Phase 6 & Phase 7: Web UI, Live API & Containerization - 2026-11-02

### Added
- **FastAPI Web API & Application Server**: Modernized lifespan application server exposing endpoints for presets, gallery renders, video generation, video analysis, and auto-editing.
- **Interactive Single-Page Web Dashboard**: Dark-mode, responsive web UI built with Tailwind CSS and Lucide icons featuring:
  - System health dashboard showing encoder mode, font engine, and LUFS target.
  - Text-to-Video creation studio with language selection, aspect ratio toggle (16:9 and 9:16), preset selection, and fast preview switch.
  - Auto-Editor & EDL workspace with filler/silence removal and punch-in zoom controls.
  - Video Gallery with real-time video playback and metadata display (duration, resolution, LUFS).
- **Containerization & Deployment**:
  - `Dockerfile`: Multi-stage Debian Bookworm image bundling Python 3.11, FFmpeg with `libass` and `libharfbuzz`, Bengali Noto fonts, and healthchecks.
  - `docker-compose.yml`: One-click containerized deployment with volume mounts and auto-restarts.
- **Automated Web API Test Suite**: `backend/tests/test_phase6_web_api.py` covering all FastAPI endpoints and achieving 30/30 total passing test cases across the entire codebase.

## [0.5.0] - Phase 5: Auto-Edit Engine (Module B) - 2026-11-02

### Added
- **Rule-Based Cut & Continuity Validator** (`CutValidator`): Enforces word boundary safety (no mid-word cuts), minimum shot continuity (>= 0.8s), natural breath padding (0.12s cushion), and aggressiveness presets (`gentle`, `balanced`, `aggressive`).
- **EDL-to-Timeline Compiler** (`EDLToTimelineCompiler`): Inverts cut lists into continuous kept video segments, translates surviving word timestamps to the edited timeline, and alternates 112% punch-in zooms to conceal jump cuts.
- **Auto-Reframe Engine**: Converts 16:9 widescreen footage into 9:16 vertical short format with centered subject framing.
- **Unified Multi-Stream Video Segment Rendering**: Updates `TimelineRenderer` to handle video sources, cutting segments via `-ss`, scaling, and applying virtual camera punch-in zooms.
- **Auto-Edit Pipeline Coordinator** (`AutoEditPipeline`): Complete end-to-end editing workflow producing Before/After comparison analytics (duration change, time saved, LUFS change, cuts applied).
- **CLI Command**: `studio edit <video_path> --goal "talking_head_polish" --aggressiveness balanced --aspect 16:9|9:16 --punch-zooms --captions --music`.

## [0.4.0] - Phase 4: Video Ingest & Multimodal Analysis - 2026-11-02

### Added
- **Video Ingestion & Normalization** (`VideoIngestor`): Handles MP4/MOV/MKV/WebM, probes container specs, extracts 16kHz mono WAV for audio processing, and generates fast CFR 720p/540p editing proxies.
- **Speech Intelligence & Filler Detection** (`SpeechAnalyzer`): Identifies words, pauses, stutters, and flags Bengali filler words (`মানে`, `ইয়ে`, `আসলে`) and English filler words (`um`, `uh`, `basically`).
- **Audio Quality Analyzer** (`AudioQualityAnalyzer`): Maps dead air intervals via FFmpeg `silencedetect`, checks True Peak, clipping, and integrated loudness (-14 LUFS target).
- **Visual Structure & Shot Boundary Detection** (`VisualSceneAnalyzer`): Integrates PySceneDetect and FFmpeg scene filters, extracts shot keyframes, and evaluates frame brightness and contrast.
- **Multimodal Video Analyzer Coordinator** (`MultimodalVideoAnalyzer`): Produces structured `AnalysisReport` JSON with executive summaries, duration savings calculations, and punch-in zoom smoothing recommendations.
- **CLI Command**: `studio analyze <video_path> --lang bn|en --goal talking_head_polish --output report.json`.

## [0.3.0] - Phase 3: Quality & Polish for Module A - 2026-11-02

### Added
- **Templates & Presets System**: Catalog of style presets (`documentary`, `short_hype`, `clean_corporate`, `news_flash`) managed by `PresetManager`.
- **Brand Kit & Watermark Engine**: Real-time watermark overlay with custom scaling, opacity, and positioning (`top_right`, `top_left`, `bottom_right`, `bottom_left`).
- **Transition SFX**: Sound effects engine mixing whoosh and hit transitions on scene cuts.
- **Image Generation Provider**: `ImageGenProvider` interface with zero-cost procedural gradient card generator (`MockImageGenProvider`) creating scene-specific visuals.
- **Thumbnail & SEO Generator**: Automated high-CTR thumbnail extraction with text banner overlay, YouTube/TikTok title candidates, description, hashtags, and timestamped chapters.
- **Cost & Attribution Tracker**: Real-time budget tracking with hard spending caps and auto-export of `credits.txt` tracking asset licensing.
- **Ultra-Fast Preview Render Mode**: 1.6-second preview rendering at 540p/720p with `ultrafast` preset for instant iterative feedback.
- **CLI Commands**: Added `studio presets` and extended `studio create` with `--preset`, `--watermark`, and `--preview` options.

## [0.2.0] - Phase 2: Text-to-Video MVP - 2026-11-02

### Added
- Complete **Text → Video Pipeline** (`CreateVideoPipeline`) linking Script Generation, Neural TTS, Word Alignment, Ken Burns Visual Assembly, Subtitle Burning, and Audio Mastering.
- **Timeline Renderer** (`TimelineRenderer`): High-throughput FFmpeg filter graph engine compiling Canonical Timelines into broadcast MP4s.
- **Audio Sidechain Ducking & EBU R128 Mastering**: Automatically ducks ambient music under voiceover and normalizes audio to target -14.0 LUFS and -1.0 dBTP.
- **Multi-Aspect Ratio Support**: Automated canvas compilation for 16:9 YouTube landscape (1920x1080) and 9:16 Shorts/Reels/TikTok vertical (1080x1920).
- **Automated Post-Render QA**: Checks file integrity, duration accuracy, stream presence, and integrated LUFS tolerance.
- **CLI Command**: `studio create --prompt "..." --lang bn|en --aspect 16:9|9:16 --output "..."`.
- **Verified Demonstration Outputs**:
  - `data/renders/bangla_demo_mvp.mp4` (1080p, 10.17s, -14.6 LUFS, Bengali karaoke captions).
  - `data/renders/english_demo_9x16.mp4` (9:16 vertical, 10.08s, -14.7 LUFS, English karaoke captions).

## [0.1.0] - Phase 0 & Phase 1 Foundation - 2026-11-02

### Added
- Complete architecture documentation, ADRs (Media Engine, Queue, Bangla Shaping, Timeline Schema, Providers).
- Pydantic v2 Timeline JSON Schema with strict validation for tracks, clips, keyframes, transitions, and effects.
- Core configuration module with environment validation (`pydantic-settings`).
- Thread-safe persistent in-process job queue with retry, exponential backoff, and state machines.
- `studio doctor` diagnostics CLI checking Python, FFmpeg (`libass`, `libharfbuzz`), audio codecs, GPU/acceleration, and Bangla fonts.
- Bangla font bundler (`Noto Sans Bengali` & `Roboto` in `assets/fonts/`).
- FFmpeg libass HarfBuzz subtitle verification test rendering complex conjuncts.
- Provider interface contracts (`LLMProvider`, `TTSProvider`, `ASRProvider`) with free high-fidelity fallback (`EdgeTTSProvider`) and mock providers for determinism.
- FastAPI REST API skeleton and Typer CLI commands.
