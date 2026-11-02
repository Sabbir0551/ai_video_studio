import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from backend.app.core.logging import logger
from backend.app.core.config import settings


class FFmpegWrapper:
    """Production-grade wrapper for FFmpeg & ffprobe operations with argument arrays and safe path escaping."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._check_installed()

    def _check_installed(self) -> bool:
        return shutil.which(self.ffmpeg_path) is not None and shutil.which(self.ffprobe_path) is not None

    def get_hardware_acceleration(self) -> str:
        """Detect and verify functional hardware video encoder (NVENC, D3D11VA, or CPU fallback)."""
        candidates = ["h264_nvenc", "h264_d3d11va", "h264_videotoolbox", "h264_qsv"]
        for enc in candidates:
            try:
                # Test 1-frame dummy encode to ensure runtime driver DLLs are loadable
                test_cmd = [
                    self.ffmpeg_path, "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.04",
                    "-c:v", enc,
                    "-f", "null", "-"
                ]
                res = subprocess.run(test_cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    return enc
            except Exception:
                continue
        return "libx264"

    def probe_media(self, file_path: str) -> Dict[str, Any]:
        """Extract stream metadata, duration, resolution, audio specs via ffprobe JSON."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"ffprobe failed on {file_path}: {res.stderr}")
        return json.loads(res.stdout)

    def measure_lufs(self, audio_path: str) -> Dict[str, float]:
        """Measure integrated LUFS, loudness range (LRA), and true peak via ebur128 filter."""
        cmd = [
            self.ffmpeg_path,
            "-i", audio_path,
            "-af", "ebur128=framelog=verbose",
            "-f", "null",
            "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        stderr = res.stderr

        # Parse Summary values from stderr
        lufs = -70.0
        true_peak = -70.0
        for line in stderr.splitlines():
            line_strip = line.strip()
            if "I:" in line_strip and "LUFS" in line_strip:
                parts = line_strip.split()
                try:
                    lufs = float(parts[1])
                except (ValueError, IndexError):
                    pass
            elif "Peak:" in line_strip and "dBFS" in line_strip:
                parts = line_strip.split()
                try:
                    true_peak = float(parts[1])
                except (ValueError, IndexError):
                    pass
        return {"integrated_lufs": lufs, "true_peak_db": true_peak}

    def normalize_filter_path(self, path: str) -> str:
        """Escape Windows drive letter and forward-slashes for FFmpeg filter chains."""
        abs_path = os.path.abspath(path).replace("\\", "/")
        # In FFmpeg filter parameters on Windows, replace ':' with '\\:'
        if len(abs_path) > 1 and abs_path[1] == ":":
            abs_path = abs_path[0] + "\\:" + abs_path[2:]
        return abs_path

    def render_color_frame_with_ass(
        self,
        ass_path: str,
        output_png: str,
        fonts_dir: Optional[str] = None,
        width: int = 1920,
        height: int = 1080,
        duration: float = 1.0
    ) -> bool:
        """Render a single verification frame with HarfBuzz libass subtitle burn-in."""
        norm_ass = self.normalize_filter_path(ass_path)
        fonts_param = ""
        if fonts_dir:
            norm_fonts = self.normalize_filter_path(fonts_dir)
            fonts_param = f":fontsdir='{norm_fonts}'"

        filter_str = f"ass='{norm_ass}'{fonts_param}"
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duration}",
            "-vf", filter_str,
            "-frames:v", "1",
            output_png
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg render frame error: {res.stderr}")
            return False
        return True

    def build_audio_ducking_filter(
        self,
        voice_label: str = "0:a",
        music_label: str = "1:a",
        threshold_db: float = -24.0,
        reduction_db: float = -12.0,
        target_lufs: float = -14.0,
        true_peak: float = -1.0
    ) -> str:
        """Generate sidechain ducking + EBU R128 mastering audio filter graph."""
        ratio = 4.0
        attack = 20.0
        release = 300.0
        filter_graph = (
            f"[{music_label}][{voice_label}]sidechaincompress="
            f"threshold={threshold_db}dB:ratio={ratio}:attack={attack}:release={release}[ducked_music];"
            f"[ducked_music][{voice_label}]amix=inputs=2:duration=longest:dropout_transition=2[mixed_audio];"
            f"[mixed_audio]loudnorm=I={target_lufs}:TP={true_peak}:LRA=11[outa]"
        )
        return filter_graph


ffmpeg = FFmpegWrapper()
