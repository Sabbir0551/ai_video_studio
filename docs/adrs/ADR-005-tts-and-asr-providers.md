# ADR-005: TTS & ASR Provider Strategy with Zero-Cost Native Fallbacks

## Status
Accepted

## Context
Video creation requires text-to-speech with natural pronunciation, especially for Bangla and English.
Video editing requires speech-to-text with word-level timestamps, speaker identification, and code-switching handling (mixing English and Bangla).
A commercial studio requires support for premium paid APIs (ElevenLabs, OpenAI, Google Cloud, Azure Speech), but a self-hosted studio must run without mandatory paid subscriptions.

## Decision
1. **TTS Architecture**:
   - Provider interface (`TTSProvider`) supporting `ElevenLabs`, `GoogleCloudTTS`, `AzureSpeech`, and `OpenAITTS`.
   - **Default Free Fallback**: `EdgeTTSProvider` using Microsoft's neural voices (`bn-BD-PradeepNeural`, `bn-BD-NabanitaNeural` for Bangla; `en-US-GuyNeural`, `en-US-JennyNeural` for English). Requires zero API keys, produces studio-grade natural prosody, and emits sentence/word boundaries.
   - **Local Offline Fallback**: Meta `mms-tts-ben` (Massively Multilingual Speech) for completely disconnected environments.

2. **ASR Architecture**:
   - Provider interface (`ASRProvider`) supporting OpenAI Whisper API, WhisperX, and `faster-whisper` (CTranslate2).
   - Word-level timestamps and code-switching detection for Bengali and English.
   - Pronunciation & text normalization pre-pass converting Bengali numerals (`১২০০` -> `বারো শত` / `এক হাজার দুই শত`), dates, currency symbols (`৳`, `BDT`), and abbreviation glossaries into speakable phonetic representations.
