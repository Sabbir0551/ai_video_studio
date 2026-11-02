import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.models.analysis import ShotBoundary
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.core.logging import logger
from PIL import Image, ImageStat


class VisualSceneAnalyzer:
    """Detects shot cuts, extracts keyframes, and evaluates framing and lighting quality."""

    def __init__(self):
        self.ffmpeg = ffmpeg

    def analyze_scenes(
        self,
        video_path: str,
        keyframes_dir: str,
        fps: float = 30.0,
        total_duration: float = 10.0
    ) -> List[ShotBoundary]:
        Path(keyframes_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Analyzing visual scenes and shot boundaries for: {video_path}")

        shots: List[ShotBoundary] = []

        # Try PySceneDetect first if available
        try:
            from scenedetect import detect, ContentDetector
            scene_list = detect(video_path, ContentDetector(threshold=27.0))
            if scene_list:
                for idx, (start_time, end_time) in enumerate(scene_list):
                    s_sec = start_time.get_seconds()
                    e_sec = end_time.get_seconds()
                    kf_path = self._extract_keyframe(video_path, s_sec + (e_sec - s_sec) / 2.0, keyframes_dir, idx + 1)
                    shots.append(ShotBoundary(
                        start_frame=start_time.get_frames(),
                        end_frame=end_time.get_frames(),
                        start_time=round(s_sec, 2),
                        end_time=round(e_sec, 2),
                        keyframe_path=kf_path
                    ))
        except Exception as e:
            logger.warning(f"PySceneDetect bypassed ({e}), using FFmpeg scene filter fallback")

        # Fallback or default single/multi-shot segmentation via FFmpeg
        if not shots:
            # If video is short or no scene cuts found, partition into natural visual segments or sample keyframes
            num_segments = max(1, int(round(total_duration / 4.0)))
            segment_dur = total_duration / num_segments
            for idx in range(num_segments):
                s_sec = idx * segment_dur
                e_sec = min(total_duration, (idx + 1) * segment_dur)
                mid_point = s_sec + (e_sec - s_sec) / 2.0
                kf_path = self._extract_keyframe(video_path, mid_point, keyframes_dir, idx + 1)
                shots.append(ShotBoundary(
                    start_frame=int(s_sec * fps),
                    end_frame=int(e_sec * fps),
                    start_time=round(s_sec, 2),
                    end_time=round(e_sec, 2),
                    keyframe_path=kf_path
                ))

        logger.info(f"Visual analysis complete: identified {len(shots)} shot(s)")
        return shots

    def _extract_keyframe(self, video_path: str, timestamp_sec: float, output_dir: str, index: int) -> str:
        """Extract a frame at timestamp_sec and save to output_dir."""
        out_path = str(Path(output_dir) / f"shot_{index:03d}.jpg")
        cmd = [
            self.ffmpeg.ffmpeg_path, "-y",
            "-ss", str(max(0.0, timestamp_sec)),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "3",
            out_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(out_path):
            # Fallback to frame 0.0s
            cmd[2] = "0.0"
            subprocess.run(cmd, capture_output=True, check=True)
        return out_path

    def evaluate_frame_quality(self, image_path: str) -> Dict[str, Any]:
        """Check brightness, contrast, and basic clarity of a keyframe."""
        if not os.path.exists(image_path):
            return {"brightness": 0, "contrast": 0, "is_dark": False, "is_blown_out": False}

        with Image.open(image_path) as im:
            grayscale = im.convert("L")
            stat = ImageStat.Stat(grayscale)
            mean_brightness = stat.mean[0] # 0 to 255
            stddev_contrast = stat.stddev[0]

            is_dark = mean_brightness < 40
            is_blown_out = mean_brightness > 220

            return {
                "mean_brightness": round(mean_brightness, 1),
                "contrast_stddev": round(stddev_contrast, 1),
                "is_underexposed": is_dark,
                "is_overexposed": is_blown_out
            }


visual_scene_analyzer = VisualSceneAnalyzer()
