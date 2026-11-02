# Bangla Video Production & Typography Guide

Bangla (বাংলা) is a first-class language in AI Video Studio. Delivering broadcast-quality Bangla video requires solving four critical challenges:

1. **Complex Text Shaping (HarfBuzz)**: Rendering conjuncts (`যুক্তাক্ষর`), vowel signs (`কার`), and consonant modifiers (`ফলা`).
2. **Text Normalization for TTS**: Transforming numerals, dates, acronyms, and symbols into speakable phonetics.
3. **Pacing and Prosody**: Calibrating speech rate (typically 125–135 words per minute for Bengali vs 145–160 for English).
4. **Code-Switching**: Accurately transcribing and synthesizing mixed Bangla-English phrasing common in modern tech and educational media.

---

## 1. Typography and HarfBuzz Subtitles

### The Problem
Naive character renderers fail when handling glyph reordering:
- Pre-base vowel signs: In `দেশ`, `ে` is typed after `দ` but displayed to the left of `দ`.
- Conjuncts: In `বিজ্ঞান`, `জ + ঞ` ligates into `জ্ঞ`.
- Reph and Hasant: In `বর্ণ`, `র + ্ + ণ` renders `র্ণ`.

### The Solution in AI Video Studio
- All captions are compiled into **ASS (Advanced SubStation Alpha)** with libass rendering backed by **HarfBuzz** and **FriBidi**.
- Fonts are bundled directly in `assets/fonts/`:
  - `Noto Sans Bengali` (Clean, modern explainer style)
  - `Kalpurush` / `SolaimanLipi` / `Nirmala UI`
- Subtitle safe zones are strictly calculated for 16:9 (bottom safe margin: 40px) and 9:16 vertical shorts (bottom safe margin: 250px to clear TikTok/Reels UI buttons).

---

## 2. Text Normalization Pipeline

Before text is sent to TTS, it passes through `backend.app.media.bangla_shaper.normalize_bangla_text_for_speech()`:

| Raw Input | Normalized Spoken Output |
| :--- | :--- |
| `২০২৬ সাল` | `দুই হাজার ছাব্বিশ সাল` |
| `১২০০ টাকা` | `বারো শত টাকা` |
| `ডা. করিম` | `ডাক্তার করিম` |
| `৫.৫%` | `পাঁচ দশমিক পাঁচ শতাংশ` |
| `২৫শে মার্চ` | `পঁচিশে মার্চ` |

---

## 3. Recommended Voices

| Engine | Voice ID | Description | Cost |
| :--- | :--- | :--- | :--- |
| **Edge-TTS (Default)** | `bn-BD-PradeepNeural` | Male, natural Dhaka prosody, studio clarity | Free |
| **Edge-TTS (Default)** | `bn-BD-NabanitaNeural` | Female, expressive, friendly | Free |
| **ElevenLabs** | Multilingual v2 | High emotional depth & voice cloning | Paid API |
| **Google Cloud** | `bn-BD-Neural2-A/B` | Broadcast announcer style | Paid API |
| **Meta MMS** | `facebook/mms-tts-ben` | Fully offline, on-device neural TTS | Free / Local |
