# ADR-001: Video Rendering & Assembly Engine

## Status
Accepted

## Context
The video studio requires high-throughput video composition (cutting, scaling, concatenating, transitions, Ken Burns motion, audio mixing, and caption overlay).
Candidates evaluated:
1. Pure MoviePy (Python library wrapping FFmpeg via pipes).
2. Pure Remotion (React + Chromium Headless).
3. Direct FFmpeg Filter Graph Compiler with Libass.
4. Hybrid: FFmpeg Core Filter Graphs + Libass Subtitles + optional Remotion for complex dynamic HTML overlays.

## Decision
We select **Direct FFmpeg Filter Graphs + Libass** as the primary rendering engine, with an optional Remotion bridge for dynamic kinetic React templates.

## Rationale
- **Performance**: Direct FFmpeg filter graphs execute in C/assembly with zero intermediate Python pipe serialization overhead. It handles multi-stream hardware acceleration (NVENC, D3D11VA, VideoToolbox) and threaded filtering.
- **Bangla Text Shaping**: FFmpeg's `libass` filter natively integrates HarfBuzz and FriBidi, providing 100% correct glyph shaping, conjunct ligation, and vowel placement for Bengali text without needing a browser engine.
- **Portability**: FFmpeg is a self-contained static binary; it does not require Chrome/Puppeteer daemon running for basic 1080p renders, ensuring fast lightweight deployment on local laptops or cloud containers.
- **MoviePy Limitations**: MoviePy (v1/v2) has known memory leaks with large video batches, slow frame iteration, and fragile audio sync. Using direct FFmpeg commands with strict argument arrays avoids shell injection and guarantees frame-accurate sync.
