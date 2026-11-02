import os
import edge_tts
from pathlib import Path
from typing import List, Optional
from backend.app.core.logging import logger
from backend.app.providers.base import TTSProvider, TTSResult
from backend.app.models.timeline import WordTimestamp
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.media.bangla_shaper import normalize_bangla_text_for_speech


class EdgeTTSProvider(TTSProvider):
    """
    High-fidelity neural TTS provider with genre-aware voice selection & prosody tuning.
    - Specialized voices for children's stories/animation, documentaries, and news.
    - Natural inflection and automatic fallback if custom prosody is unsupported.
    """

    VOICE_PROFILES = {
        "bn": {
            "default": "bn-BD-PradeepNeural",
            "gentle_story": "bn-BD-NabanitaNeural",
            "cheerful_cartoon": "bn-BD-NabanitaNeural",
            "documentary": "bn-IN-BashkarNeural"
        },
        "en": {
            "default": "en-US-GuyNeural",
            "gentle_story": "en-US-AnaNeural",
            "cheerful_cartoon": "en-US-AnaNeural",
            "documentary": "en-US-ChristopherNeural"
        }
    }

    @property
    def name(self) -> str:
        return "edge-tts"

    def select_voice(self, language: str, content_hint: str = "") -> str:
        """Select the most expressive neural voice based on language and content tone."""
        lang_key = "bn" if language.startswith("bn") else "en"
        profiles = self.VOICE_PROFILES[lang_key]

        c_lower = content_hint.lower()
        if any(w in c_lower for w in ["toddler", "children", "baby", "cartoon", "nursery", "kids", "buli", "cute", "story"]):
            return profiles["gentle_story"]
        elif any(w in c_lower for w in ["documentary", "history", "deep", "serious"]):
            return profiles["documentary"]
        return profiles["default"]

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_path: str = "output.mp3",
        language: str = "bn",
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        content_hint: str = "",
        **kwargs
    ) -> TTSResult:
        if not voice_id:
            voice_id = self.select_voice(language, content_hint=content_hint or text)

        # Pre-normalize text for natural pronunciation
        clean_text = normalize_bangla_text_for_speech(text) if language.startswith("bn") else text

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async def _run_stream(comm: edge_tts.Communicate) -> List[WordTimestamp]:
            words: List[WordTimestamp] = []
            with open(output_path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start_sec = chunk["offset"] / 10_000_000.0
                        dur_sec = chunk["duration"] / 10_000_000.0
                        words.append(WordTimestamp(
                            word=chunk["text"],
                            start=round(start_sec, 3),
                            end=round(start_sec + dur_sec, 3)
                        ))
            return words

        word_boundaries: List[WordTimestamp] = []
        try:
            # Try with rate/pitch if provided
            if rate or pitch:
                comm = edge_tts.Communicate(clean_text, voice_id, rate=rate or "+0%", pitch=pitch or "+0Hz")
                word_boundaries = await _run_stream(comm)
            else:
                comm = edge_tts.Communicate(clean_text, voice_id)
                word_boundaries = await _run_stream(comm)
        except Exception as e:
            logger.warning(f"Voice synthesis with custom parameters failed ({e}), retrying with standard baseline...")
            comm = edge_tts.Communicate(clean_text, voice_id)
            word_boundaries = await _run_stream(comm)

        # Probe exact audio file duration using ffprobe
        probe = ffmpeg.probe_media(output_path)
        duration = float(probe.get("format", {}).get("duration", 0.0))

        # Fallback word timestamps if WordBoundary events were missing
        if not word_boundaries and duration > 0.0:
            words = clean_text.split()
            if words:
                time_per_word = duration / len(words)
                for idx, w in enumerate(words):
                    w_start = round(idx * time_per_word, 3)
                    w_end = round((idx + 1) * time_per_word, 3)
                    word_boundaries.append(WordTimestamp(word=w, start=w_start, end=w_end))

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=word_boundaries,
            provider_name=self.name,
            cost_usd=0.0
        )
