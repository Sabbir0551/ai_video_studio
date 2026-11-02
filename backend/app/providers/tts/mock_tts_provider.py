import subprocess
from pathlib import Path
from typing import Optional, List
from backend.app.providers.base import TTSProvider, TTSResult
from backend.app.models.timeline import WordTimestamp


class MockTTSProvider(TTSProvider):
    """Deterministic offline TTS provider for testing pipelines without network calls."""

    @property
    def name(self) -> str:
        return "mock-tts"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_path: str = "mock_audio.mp3",
        language: str = "bn",
        **kwargs
    ) -> TTSResult:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        words = text.split()
        # Calibrate roughly 0.4s per word
        duration = max(1.0, round(len(words) * 0.4, 2))

        # Generate silent MP3 via FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-q:a", "9",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        word_timestamps: List[WordTimestamp] = []
        time_per_word = duration / max(1, len(words))
        for idx, w in enumerate(words):
            word_timestamps.append(WordTimestamp(
                word=w,
                start=round(idx * time_per_word, 3),
                end=round((idx + 1) * time_per_word, 3)
            ))

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=word_timestamps,
            provider_name=self.name,
            cost_usd=0.0
        )
