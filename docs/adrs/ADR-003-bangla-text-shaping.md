# ADR-003: Bangla Text Shaping & Typography Engine

## Status
Accepted

## Context
Bangla (Bengali) script requires complex text layout (CTL):
1. **Pre-base vowel signs** (`ি`, `ে`, `ৈ` must be rendered visually before the consonant, even though typed after).
2. **Post-base vowel signs** (`া`, `ী`, `ৌ`).
3. **Below-base and above-base vowel signs** (`ু`, `ূ`, `ৃ`, `ঁ`).
4. **Conjuncts / Yuktakkhor** (`ক্ষ` [ক+ষ], `জ্ঞ` [জ+ঞ], `ব্দ` [ব+দ], `ঙ্ক` [ঙ+ক], `ত্র` [ত+র-ফলা], etc.).
5. **Hasant & Reph** (`র্` [র+হসন্ত]).

Naive pixel rendering or basic character-by-character renderers fail catastrophically by drawing disconnected squares or misplacing vowel signs.

## Decision
1. **Never use naive rasterization**.
2. Subtitles and burned-in captions must be compiled into **Advanced SubStation Alpha (ASS v4+)** format rendered through **libass** (which links HarfBuzz and FriBidi).
3. Graphic titles, thumbnails, and lower-thirds use **Pillow with libraqm** (HarfBuzz) or Chromium/Remotion DOM rendering.
4. Bundle high-grade OpenType Bengali fonts (`Noto Sans Bengali`, `Hind Siliguri`, `Kalpurush`) directly in `assets/fonts/` and register them via FFmpeg `fontsdir`.
5. Maintain a dedicated automated test suite (`test_bangla_rendering.py`) rendering sentences with the most intricate Bengali conjuncts and verifying pixel layout.
