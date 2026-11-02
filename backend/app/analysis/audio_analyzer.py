import re
import subprocess
from typing import List, Dict, Any, Tuple
from backend.app.models.analysis import AudioAnalysis
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.core.logging import logger


class AudioQualityAnalyzer:
    """Extracts loudness metrics (LUFS), True Peak, silence intervals, and clipping from audio tracks."""

    def __init__(self):
        self.ffmpeg = ffmpeg

    def analyze_audio(self, audio_wav_path: str, silence_threshold_db: float = -32.0, min_silence_duration: float = 0.5) -> AudioAnalysis:
        logger.info(f"Analyzing audio stream: {audio_wav_path}")

        # 1. Detect silences using FFmpeg silencedetect filter
        silence_cmd = [
            self.ffmpeg.ffmpeg_path,
            "-i", audio_wav_path,
            "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}",
            "-f", "null",
            "-"
        ]
        res_silence = subprocess.run(silence_cmd, capture_output=True, text=True)
        stderr_silence = res_silence.stderr

        silence_segments: List[List[float]] = []
        current_start = None

        for line in stderr_silence.splitlines():
            line_strip = line.strip()
            if "silence_start:" in line_strip:
                match = re.search(r"silence_start:\s*([0-9.]+)", line_strip)
                if match:
                    current_start = float(match.group(1))
            elif "silence_end:" in line_strip and current_start is not None:
                match = re.search(r"silence_end:\s*([0-9.]+)", line_strip)
                if match:
                    end = float(match.group(1))
                    silence_segments.append([round(current_start, 3), round(end, 3)])
                    current_start = None

        # 2. Measure LUFS and Peak
        lufs_info = self.ffmpeg.measure_lufs(audio_wav_path)
        integrated_lufs = lufs_info.get("integrated_lufs", -70.0)
        true_peak_db = lufs_info.get("true_peak_db", -70.0)

        # 3. Check for clipping & noise floor via astats
        astats_cmd = [
            self.ffmpeg.ffmpeg_path,
            "-i", audio_wav_path,
            "-af", "astats=metadata=1:reset=1",
            "-f", "null",
            "-"
        ]
        res_astats = subprocess.run(astats_cmd, capture_output=True, text=True)
        has_clipping = "Flat factor" in res_astats.stderr or true_peak_db >= -0.1

        noise_floor_db = -60.0
        match_noise = re.search(r"RMS level dB:\s*([-\d.]+)", res_astats.stderr)
        if match_noise:
            try:
                noise_floor_db = float(match_noise.group(1))
            except ValueError:
                pass

        logger.info(f"Audio analysis complete: LUFS={integrated_lufs:.1f}, Peak={true_peak_db:.1f}dB, Silences={len(silence_segments)}")
        return AudioAnalysis(
            integrated_lufs=round(integrated_lufs, 2),
            true_peak_db=round(true_peak_db, 2),
            silence_segments=silence_segments,
            has_clipping=has_clipping,
            noise_floor_db=round(noise_floor_db, 2)
        )


audio_quality_analyzer = AudioQualityAnalyzer()
