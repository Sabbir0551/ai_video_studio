# AI Video Studio Architecture

## 1. System Overview

AI Video Studio is a modular, event-driven personal video creation and auto-editing engine. It combines multimodal LLM orchestration, neural voice synthesis (TTS), automatic speech recognition (ASR), and frame-accurate media composition via FFmpeg.

```mermaid
flowchart TD
    subgraph Inputs
        TXT["Text / Article / Script / URL"]
        VID["Raw Uploaded Video"]
        ASSETS["User Images & Brand Kit"]
    end

    subgraph API_and_CLI["API & CLI Layer"]
        CLI["Typer CLI (studio)"]
        FASTAPI["FastAPI REST & WebSocket"]
    end

    subgraph Orchestration["Job Orchestration & State"]
        QUEUE["Persistent Queue (SQLite / Redis)"]
        STATE["Job State Machine (Cached / Resumable)"]
        DB[(Metadata DB: SQLite/Postgres)]
    end

    subgraph Pipeline_A["Module A: Text -> Video Pipeline"]
        LLM_SCRIPT["LLM Script & Storyboard Generator"]
        TTS_ENGINE["TTS Voiceover & Word Alignment"]
        VIS_MATCHER["Visual Asset Matcher (User / Stock / AI)"]
        MOTION_GEN["Ken Burns & Motion Generator"]
        AUDIO_MIXER["Audio Master (-14 LUFS + Ducking)"]
    end

    subgraph Pipeline_B["Module B: Video Upload -> Auto-Edit Pipeline"]
        INGEST["Ingest & Audio Extractor"]
        ANALYZER["Multimodal Analyzer (Whisper + PySceneDetect)"]
        EDL_GEN["LLM Edit Decision List (Silence/Filler/Zooms)"]
        CUT_VALIDATOR["Cut Safety & Continuity Validator"]
    end

    subgraph Intermediate_Model["Canonical Intermediate Model"]
        TIMELINE["Timeline JSON Schema (Tracks, Clips, FX, Captions)"]
        EDL_VIEW["Interactive Human-in-the-Loop Review"]
    end

    subgraph Media_Engine["Media Engine & QA"]
        HARFBUZZ["Bangla HarfBuzz / Libass Shaper"]
        FFMPEG["FFmpeg Filter Graph Compiler"]
        QA["Post-Render Automated QA (LUFS, Sync, Glitches)"]
        OUTPUT["Final 1080p / 9:16 / 1:1 Video"]
    end

    TXT --> FASTAPI
    VID --> FASTAPI
    ASSETS --> FASTAPI
    FASTAPI --> QUEUE
    CLI --> QUEUE
    QUEUE --> STATE
    STATE --> DB

    STATE --> Pipeline_A
    STATE --> Pipeline_B

    Pipeline_A --> TIMELINE
    Pipeline_B --> TIMELINE

    TIMELINE --> EDL_VIEW
    EDL_VIEW --> FFMPEG
    HARFBUZZ --> FFMPEG
    FFMPEG --> QA
    QA --> OUTPUT
```

## 2. Directory Layout and Storage

The studio maintains an explicit directory structure per project:
```
data/
└── projects/
    └── <project_id>/
        ├── project.json          # Project metadata & configuration
        ├── inputs/               # Original uploaded images, videos, audio, text
        ├── cache/                # Stage hashes, intermediate TTS wavs, proxies
        │   ├── tts/
        │   ├── transcripts/
        │   └── thumbnails/
        ├── audio/                # Mastered voiceover, ducked music bed, sfx
        ├── timeline/             # timeline.json (Canonical schema), revisions
        ├── renders/              # Final exported videos (1080p, shorts, proxies)
        └── logs/                 # Structured execution logs and stage metrics
```

## 3. Pipeline Stages

### Module A: Text-to-Video Pipeline
1. **Content Understanding & Scripting**: Generates hooked narration, calibrated to speaking rate (e.g. 130 words/min in Bangla, 150 words/min in English).
2. **Storyboard Breakdown**: Structures scenes with narration, visual intent, visual asset priority, and transition cues.
3. **Voiceover & Word Alignment**: Produces scene audio and word-level timestamps (`start`, `end`, `word`).
4. **Visual Sourcing & Preprocessing**: Matches user images first, falls back to stock/AI; applies smart crop, safe margins, and Ken Burns easing.
5. **Timeline Compilation**: Compiles scenes, audio, and animated subtitles into `Timeline` JSON.
6. **Mastering & Rendering**: Sidechain music ducking under voice, EBU R128 (-14 LUFS) normalization, libass Bengali subtitle burn-in, FFmpeg render.
7. **Automated QA**: Checks duration, audio levels, black frames, and video integrity.

### Module B: Video Upload & Auto-Edit Pipeline
1. **Ingest & Proxy**: Normalizes input video to constant frame rate (CFR) and generates a fast editing proxy.
2. **Multimodal Analysis**:
   - Audio: Whisper transcription, silence detection, filler words (`মানে`, `ইয়ে`, `um`, `uh`), loudness map.
   - Video: Shot boundary detection, keyframes, face saliency tracking.
3. **Edit Decision Engine**: Generates cuts for silences and fillers, punch-in zooms (110%-115%) to smooth jump cuts, B-roll cutaway placement, and 9:16 re-framing.
4. **Rule-Based Cut Validator**: Guarantees no cuts occur mid-word or violate minimum shot durations.
5. **Human Checkpoint**: Presents decisions for user approval before rendering.
6. **Render & Delivery**: Executes smart re-encoding from the original source files.
