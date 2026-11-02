import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.media.ffmpeg_wrapper import ffmpeg


class IngestResult:
    def __init__(
        self,
        original_path: str,
        proxy_video_path: str,
        audio_wav_path: str,
        duration: float,
        width: int,
        height: int,
        fps: float,
        codec_video: str,
        codec_audio: str,
        is_vfr: bool = False
    ):
        self.original_path = original_path
        self.proxy_video_path = proxy_video_path
        self.audio_wav_path = audio_wav_path
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps
        self.codec_video = codec_video
        self.codec_audio = codec_audio
        self.is_vfr = is_vfr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_path": self.original_path,
            "proxy_video_path": self.proxy_video_path,
            "audio_wav_path": self.audio_wav_path,
            "duration": round(self.duration, 2),
            "resolution": f"{self.width}x{self.height}",
            "fps": round(self.fps, 2),
            "codec_video": self.codec_video,
            "codec_audio": self.codec_audio,
            "is_vfr": self.is_vfr
        }


class VideoIngestor:
    """Ingests, validates, normalizes, and generates low-res editing proxies and audio tracks."""

    def __init__(self):
        self.ffmpeg = ffmpeg

    def ingest(self, input_video_path: str, work_dir: str) -> IngestResult:
        if not os.path.exists(input_video_path):
            raise FileNotFoundError(f"Input video file not found: {input_video_path}")

        work_path = Path(work_dir)
        work_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Ingesting media: {input_video_path}")
        probe = self.ffmpeg.probe_media(input_video_path)
        format_info = probe.get("format", {})
        streams = probe.get("streams", [])

        duration = float(format_info.get("duration", 0.0))
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            raise ValueError(f"File {input_video_path} does not contain any video stream.")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec_v = video_stream.get("codec_name", "unknown")
        codec_a = audio_stream.get("codec_name", "none") if audio_stream else "none"

        fps = 30.0
        if "r_frame_rate" in video_stream:
            parts = video_stream["r_frame_rate"].split("/")
            if len(parts) == 2 and float(parts[1]) > 0:
                fps = float(parts[0]) / float(parts[1])

        # 1. Extract 16kHz mono WAV for audio & speech analysis
        audio_wav = str(work_path / "extracted_audio_16k.wav")
        if audio_stream:
            cmd_audio = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", input_video_path,
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                audio_wav
            ]
            subprocess.run(cmd_audio, capture_output=True, check=True)
        else:
            # Generate silent wav if video has no audio
            cmd_silent = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=16000:cl=mono",
                "-t", str(duration),
                audio_wav
            ]
            subprocess.run(cmd_silent, capture_output=True, check=True)

        # 2. Generate fast CFR editing proxy (720p or 540p)
        proxy_mp4 = str(work_path / "proxy_analysis.mp4")
        proxy_w = min(1280, width)
        proxy_h = int(proxy_w * (height / width))
        if proxy_h % 2 != 0:
            proxy_h += 1

        cmd_proxy = [
            self.ffmpeg.ffmpeg_path, "-y",
            "-i", input_video_path,
            "-vf", f"scale={proxy_w}:{proxy_h}:force_original_aspect_ratio=decrease",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "26",
            "-an",
            proxy_mp4
        ]
        res = subprocess.run(cmd_proxy, capture_output=True, text=True)
        if res.returncode != 0:
            logger.warning(f"Failed to generate editing proxy, using original: {res.stderr[-200:]}")
            proxy_mp4 = input_video_path

        logger.info(f"Ingested successfully: {width}x{height} @ {fps:.1f}fps, duration: {duration:.2f}s")
        return IngestResult(
            original_path=input_video_path,
            proxy_video_path=proxy_mp4,
            audio_wav_path=audio_wav,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            codec_video=codec_v,
            codec_audio=codec_a
        )


video_ingestor = VideoIngestor()
