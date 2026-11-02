from typing import Optional, List
from backend.app.providers.asr.base import ASRProvider, ASRResult
from backend.app.models.timeline import WordTimestamp
from backend.app.media.ffmpeg_wrapper import ffmpeg


class MockASRProvider(ASRProvider):
    """Deterministic ASR provider returning structured transcript with filler words for edit testing."""

    @property
    def name(self) -> str:
        return "mock-asr"

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = "bn"
    ) -> ASRResult:
        probe = ffmpeg.probe_media(audio_path)
        duration = float(probe.get("format", {}).get("duration", 10.0))

        if language and language.startswith("bn"):
            # Sample Bengali talking-head transcript with fillers ('মানে', 'আসলে') and pauses
            raw_text = "স্বাগতম সবাইকে। মানে আজকে আমরা কথা বলব আসলে কৃত্রিম বুদ্ধিমত্তা নিয়ে।"
            words_raw = [
                ("স্বাগতম", 0.4, 0.9),
                ("সবাইকে।", 0.95, 1.5),
                ("মানে", 2.2, 2.6),       # Filler word after a 0.7s pause
                ("আজকে", 2.7, 3.1),
                ("আমরা", 3.15, 3.5),
                ("কথা", 3.55, 3.8),
                ("বলব", 3.85, 4.2),
                ("আসলে", 5.0, 5.4),       # Filler word after a 0.8s pause
                ("কৃত্রিম", 5.5, 6.1),
                ("বুদ্ধিমত্তা", 6.15, 6.9),
                ("নিয়ে।", 6.95, 7.5)
            ]
        else:
            raw_text = "Welcome everyone. Um today we are basically talking about artificial intelligence."
            words_raw = [
                ("Welcome", 0.4, 0.9),
                ("everyone.", 0.95, 1.5),
                ("Um", 2.2, 2.6),         # Filler
                ("today", 2.7, 3.1),
                ("we", 3.15, 3.3),
                ("are", 3.35, 3.5),
                ("basically", 3.6, 4.2),  # Filler
                ("talking", 4.3, 4.8),
                ("about", 4.85, 5.2),
                ("artificial", 5.8, 6.4),
                ("intelligence.", 6.45, 7.2)
            ]

        word_timestamps = [
            WordTimestamp(word=w, start=s, end=e) for w, s, e in words_raw
        ]

        return ASRResult(
            transcript_text=raw_text,
            language=language or "bn",
            duration_seconds=duration,
            words=word_timestamps,
            confidence=0.96,
            provider_name=self.name,
            cost_usd=0.0
        )
