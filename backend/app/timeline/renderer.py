import os
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.models.timeline import Timeline, TrackType, Clip
from backend.app.models.brand import BrandKit, WatermarkPosition
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.media.bangla_shaper import generate_ass_subtitle_file


class RenderQAResult:
    def __init__(
        self,
        output_path: str,
        duration: float,
        width: int,
        height: int,
        fps: float,
        integrated_lufs: float,
        file_size_bytes: int,
        render_time_seconds: float,
        passed: bool,
        notes: List[str]
    ):
        self.output_path = output_path
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps
        self.integrated_lufs = integrated_lufs
        self.file_size_bytes = file_size_bytes
        self.render_time_seconds = render_time_seconds
        self.passed = passed
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_path": self.output_path,
            "duration": round(self.duration, 2),
            "resolution": f"{self.width}x{self.height}",
            "fps": round(self.fps, 2),
            "integrated_lufs": round(self.integrated_lufs, 2),
            "file_size_bytes": self.file_size_bytes,
            "render_time_seconds": round(self.render_time_seconds, 2),
            "passed": self.passed,
            "notes": self.notes
        }


class TimelineRenderer:
    """Production-grade FFmpeg compiler and renderer for the Canonical Timeline JSON schema."""

    def __init__(self):
        self.ffmpeg = ffmpeg

    def render(
        self,
        timeline: Timeline,
        output_path: str,
        work_dir: Optional[str] = None,
        brand_kit: Optional[BrandKit] = None,
        preview_mode: bool = False
    ) -> RenderQAResult:
        start_time = time.time()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        work_path = Path(work_dir) if work_dir else Path(output_path).parent / "temp_render"
        work_path.mkdir(parents=True, exist_ok=True)

        canvas = timeline.canvas
        width = canvas.width if not preview_mode else (640 if canvas.aspect_ratio == "9:16" else 960)
        height = canvas.height if not preview_mode else (1136 if canvas.aspect_ratio == "9:16" else 540)
        fps = canvas.fps
        total_duration = max(1.0, timeline.total_duration())

        logger.info(
            f"Rendering timeline for '{timeline.project_id}' -> {output_path} "
            f"({'PREVIEW ' if preview_mode else ''}{width}x{height}@{fps}fps)"
        )

        # 1. Collect visual clips (Image or Video tracks)
        visual_track = None
        for track in timeline.tracks:
            if track.track_type in (TrackType.IMAGE, TrackType.VIDEO) and not track.muted:
                visual_track = track
                break

        if not visual_track or not visual_track.clips:
            raise ValueError("Timeline contains no active visual tracks or clips to render.")

        # 2. Render each visual scene clip to a temporary segment
        segment_files = []
        for idx, clip in enumerate(visual_track.clips):
            seg_path = str(work_path / f"scene_{idx:03d}.mp4")
            clip_dur = max(0.5, clip.timeline_end - clip.timeline_start)
            self._render_visual_clip(clip, clip_dur, width, height, fps, seg_path)
            segment_files.append(seg_path)

        # 3. Concatenate visual segments
        concat_txt = work_path / "concat_list.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for s in segment_files:
                norm_p = os.path.abspath(s).replace("\\", "/")
                f.write(f"file '{norm_p}'\n")

        raw_visual_mp4 = str(work_path / "combined_visuals.mp4")
        concat_cmd = [
            self.ffmpeg.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            raw_visual_mp4
        ]
        res = subprocess.run(concat_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Visual concatenation failed: {res.stderr}")

        # 4. Master Audio Track (Voice + Ducked Background Music + Loudness -14 LUFS)
        mastered_audio_aac = str(work_path / "mastered_audio.aac")
        self._master_audio(timeline, total_duration, mastered_audio_aac, work_path)

        # 5. Compile Subtitles into ASS format
        ass_path = str(work_path / "subtitles.ass")
        margin_v = 50 if canvas.aspect_ratio != "9:16" else 220
        font_size = 54 if canvas.aspect_ratio != "9:16" else 48
        
        has_subtitles = len(timeline.captions) > 0
        if has_subtitles:
            generate_ass_subtitle_file(
                captions=timeline.captions,
                output_path=ass_path,
                font_name="Noto Sans Bengali",
                font_size=font_size,
                play_res_x=width,
                play_res_y=height,
                margin_v=margin_v,
                highlight_active_word=True
            )

        # 6. Final Video Assembly with Subtitles and optional Watermark
        active_encoder = self.ffmpeg.get_hardware_acceleration() if not preview_mode else "libx264"
        
        # Build filter chain
        final_inputs = ["-i", raw_visual_mp4]
        has_watermark = brand_kit and brand_kit.logo_path and os.path.exists(brand_kit.logo_path)
        if has_watermark:
            final_inputs.extend(["-i", brand_kit.logo_path])

        final_inputs.extend(["-i", mastered_audio_aac])
        audio_input_idx = 2 if has_watermark else 1

        filter_complex_steps = []
        cur_v = "[0:v]"
        
        if has_watermark:
            wm_w = int(width * brand_kit.watermark_scale)
            margin = brand_kit.margin_pixels
            pos = brand_kit.watermark_position
            if pos == WatermarkPosition.TOP_LEFT:
                pos_xy = f"{margin}:{margin}"
            elif pos == WatermarkPosition.BOTTOM_RIGHT:
                pos_xy = f"W-w-{margin}:H-h-{margin}"
            elif pos == WatermarkPosition.BOTTOM_LEFT:
                pos_xy = f"{margin}:H-h-{margin}"
            else: # TOP_RIGHT
                pos_xy = f"W-w-{margin}:{margin}"

            filter_complex_steps.append(
                f"[1:v]scale={wm_w}:-1,format=rgba,colorchannelmixer=aa={brand_kit.watermark_opacity}[wm];"
                f"{cur_v}[wm]overlay={pos_xy}[v_wm]"
            )
            cur_v = "[v_wm]"

        if has_subtitles:
            norm_ass = self.ffmpeg.normalize_filter_path(ass_path)
            fonts_dir = self.ffmpeg.normalize_filter_path(str(settings.fonts_dir))
            filter_complex_steps.append(f"{cur_v}ass='{norm_ass}':fontsdir='{fonts_dir}'[v_out]")
            cur_v = "[v_out]"

        def build_cmd(encoder: str) -> List[str]:
            cmd = [self.ffmpeg.ffmpeg_path, "-y"]
            cmd.extend(final_inputs)
            
            if filter_complex_steps:
                cmd.extend(["-filter_complex", ";".join(filter_complex_steps), "-map", cur_v, "-map", f"{audio_input_idx}:a"])
            else:
                cmd.extend(["-map", "0:v", "-map", f"{audio_input_idx}:a"])

            if encoder == "h264_nvenc":
                cmd.extend(["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "22"])
            else:
                preset_speed = "ultrafast" if preview_mode else "fast"
                crf_val = "26" if preview_mode else "21"
                cmd.extend(["-c:v", "libx264", "-preset", preset_speed, "-crf", crf_val])
                
            cmd.extend([
                "-c:a", "copy",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-shortest",
                output_path
            ])
            return cmd

        final_cmd = build_cmd(active_encoder)
        logger.info(f"Rendering final export via {active_encoder}...")
        res = subprocess.run(final_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            if active_encoder != "libx264":
                logger.warning(f"Hardware encoder {active_encoder} failed, falling back to libx264: {res.stderr[-300:]}")
                fallback_cmd = build_cmd("libx264")
                res = subprocess.run(fallback_cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Final render assembly failed: {res.stderr}")
            else:
                raise RuntimeError(f"Final render assembly failed: {res.stderr}")

        # 7. Automated Post-Render QA Check
        render_duration = time.time() - start_time
        qa_result = self._run_post_render_qa(output_path, timeline, render_duration)

        # Cleanup temporary files
        try:
            shutil.rmtree(work_path, ignore_errors=True)
        except Exception:
            pass

        logger.info(f"Render completed in {render_duration:.2f}s! QA status: {'PASSED' if qa_result.passed else 'FAILED'}")
        return qa_result

    def _render_visual_clip(
        self,
        clip: Clip,
        duration: float,
        width: int,
        height: int,
        fps: int,
        output_file: str
    ) -> None:
        """Render an individual image or video clip with Ken Burns motion, punch-in zoom, and exact scaling."""
        is_video = any(clip.source_path.lower().endswith(ext) for ext in [".mp4", ".mov", ".mkv", ".webm", ".avi"])

        if is_video:
            # Video segment rendering with optional punch-in zoom
            scale_factor = clip.transform.scale if (clip.transform and clip.transform.scale) else 1.0
            if scale_factor > 1.0:
                # Punch-in zoom with centered crop
                scaled_w = int(width * scale_factor)
                scaled_h = int(height * scale_factor)
                vf = f"scale={scaled_w}:{scaled_h}:force_original_aspect_ratio=increase,crop={width}:{height}"
            else:
                vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

            cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-ss", str(clip.source_in),
                "-i", clip.source_path,
                "-t", str(duration),
                "-vf", vf,
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-an",
                output_file
            ]
        else:
            # Image rendering with Ken Burns zoompan
            total_frames = int(round(duration * fps))
            zoom_expr = f"'min(zoom+0.0015,1.08)'"
            x_expr = f"'iw/2-(iw/zoom/2)'"
            y_expr = f"'ih/2-(ih/zoom/2)'"

            scale_crop = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"zoompan=z={zoom_expr}:d={total_frames}:x={x_expr}:y={y_expr}:s={width}x{height}:fps={fps}"
            )

            cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-loop", "1",
                "-i", clip.source_path,
                "-vf", scale_crop,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                output_file
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Clip rendering failed for {clip.source_path}: {res.stderr}")

    def _master_audio(self, timeline: Timeline, duration: float, output_aac: str, work_path: Path) -> None:
        """Combine narration, background music, sfx, apply sidechain ducking and EBU R128 loudness mastering."""
        voice_track = next((t for t in timeline.tracks if t.track_type == TrackType.VOICE and not t.muted), None)
        music_track = next((t for t in timeline.tracks if t.track_type == TrackType.MUSIC and not t.muted), None)
        sfx_track = next((t for t in timeline.tracks if t.track_type == TrackType.SFX and not t.muted), None)

        voice_audio = None
        if voice_track and voice_track.clips:
            voice_audio = str(work_path / "combined_voice.mp3")
            if len(voice_track.clips) == 1:
                shutil.copy(voice_track.clips[0].source_path, voice_audio)
            else:
                voice_concat_txt = work_path / "voice_concat.txt"
                with open(voice_concat_txt, "w", encoding="utf-8") as f:
                    for c in voice_track.clips:
                        norm_p = os.path.abspath(c.source_path).replace("\\", "/")
                        f.write(f"file '{norm_p}'\n")
                cmd = [
                    self.ffmpeg.ffmpeg_path, "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(voice_concat_txt),
                    "-c:a", "libmp3lame",
                    voice_audio
                ]
                subprocess.run(cmd, capture_output=True, check=True)

        # If no separate voice track, extract and concatenate audio from edited video clips
        if not voice_audio:
            video_track = next((t for t in timeline.tracks if t.track_type == TrackType.VIDEO and not t.muted), None)
            if video_track and video_track.clips:
                video_audio_segs = []
                for idx, c in enumerate(video_track.clips):
                    seg_a = str(work_path / f"v_audio_{idx:03d}.aac")
                    clip_dur = max(0.1, c.timeline_end - c.timeline_start)
                    cmd_v_a = [
                        self.ffmpeg.ffmpeg_path, "-y",
                        "-ss", str(c.source_in),
                        "-i", c.source_path,
                        "-t", str(clip_dur),
                        "-vn",
                        "-c:a", "aac",
                        seg_a
                    ]
                    subprocess.run(cmd_v_a, capture_output=True, check=True)
                    video_audio_segs.append(seg_a)

                v_concat_txt = work_path / "v_audio_concat.txt"
                with open(v_concat_txt, "w", encoding="utf-8") as f:
                    for a in video_audio_segs:
                        norm_p = os.path.abspath(a).replace("\\", "/")
                        f.write(f"file '{norm_p}'\n")

                voice_audio = str(work_path / "combined_video_audio.aac")
                cmd_concat_a = [
                    self.ffmpeg.ffmpeg_path, "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(v_concat_txt),
                    "-c:a", "copy",
                    voice_audio
                ]
                subprocess.run(cmd_concat_a, capture_output=True, check=True)

        music_audio = None
        if music_track and music_track.clips:
            music_audio = music_track.clips[0].source_path

        sfx_audio = None
        if sfx_track and sfx_track.clips:
            sfx_audio = sfx_track.clips[0].source_path

        # If we have voice, music, and optional SFX
        if voice_audio and music_audio and sfx_audio:
            ducking_cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", voice_audio,
                "-stream_loop", "-1", "-i", music_audio,
                "-i", sfx_audio,
                "-t", str(duration),
                "-filter_complex",
                "[1:a][0:a]sidechaincompress=threshold=-24dB:ratio=4:attack=20:release=300[ducked_music];"
                "[ducked_music][0:a][2:a]amix=inputs=3:duration=first:weights=0.3 1.0 0.4[mixed_audio];"
                "[mixed_audio]loudnorm=I=-14:TP=-1.0:LRA=11[outa]",
                "-map", "[outa]",
                "-c:a", "aac",
                "-b:a", "192k",
                output_aac
            ]
            res = subprocess.run(ducking_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Audio mastering with SFX failed: {res.stderr}")
        elif voice_audio and music_audio:
            ducking_cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", voice_audio,
                "-stream_loop", "-1", "-i", music_audio,
                "-t", str(duration),
                "-filter_complex",
                "[1:a][0:a]sidechaincompress=threshold=-24dB:ratio=4:attack=20:release=300[ducked_music];"
                "[ducked_music][0:a]amix=inputs=2:duration=first[mixed_audio];"
                "[mixed_audio]loudnorm=I=-14:TP=-1.0:LRA=11[outa]",
                "-map", "[outa]",
                "-c:a", "aac",
                "-b:a", "192k",
                output_aac
            ]
            res = subprocess.run(ducking_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Audio ducking and mastering failed: {res.stderr}")
        elif voice_audio:
            # Only voice: normalize to -14 LUFS
            cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", voice_audio,
                "-t", str(duration),
                "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
                "-c:a", "aac",
                "-b:a", "192k",
                output_aac
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        elif music_audio:
            # Only music
            cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", music_audio,
                "-t", str(duration),
                "-af", "loudnorm=I=-14:TP=-1.0:LRA=11",
                "-c:a", "aac",
                "-b:a", "192k",
                output_aac
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        else:
            # Generate silent stereo track
            cmd = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=48000:cl=stereo",
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", "192k",
                output_aac
            ]
            subprocess.run(cmd, capture_output=True, check=True)

    def _run_post_render_qa(self, output_path: str, timeline: Timeline, render_time: float) -> RenderQAResult:
        notes = []
        passed = True

        if not os.path.exists(output_path):
            return RenderQAResult(
                output_path=output_path, duration=0, width=0, height=0, fps=0,
                integrated_lufs=-70, file_size_bytes=0, render_time_seconds=render_time,
                passed=False, notes=["Render output file was not created."]
            )

        file_size = os.path.getsize(output_path)
        if file_size < 10000:
            passed = False
            notes.append(f"Render output file is suspiciously small ({file_size} bytes).")

        # ffprobe validation
        probe = self.ffmpeg.probe_media(output_path)
        format_info = probe.get("format", {})
        streams = probe.get("streams", [])

        measured_duration = float(format_info.get("duration", 0.0))
        expected_duration = timeline.total_duration()
        if abs(measured_duration - expected_duration) > 1.5:
            notes.append(f"Duration deviation: measured {measured_duration:.2f}s vs expected {expected_duration:.2f}s")

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        fps_eval = 0.0
        if video_stream and "r_frame_rate" in video_stream:
            r = video_stream["r_frame_rate"].split("/")
            if len(r) == 2 and float(r[1]) > 0:
                fps_eval = float(r[0]) / float(r[1])

        # Audio LUFS validation
        lufs_data = self.ffmpeg.measure_lufs(output_path)
        integrated_lufs = lufs_data.get("integrated_lufs", -70.0)

        # Target is -14.0 LUFS (web standard) ± 2.0 LU tolerance
        if abs(integrated_lufs - timeline.audio.target_lufs) > 2.0:
            notes.append(f"Loudness deviation: {integrated_lufs:.1f} LUFS vs target {timeline.audio.target_lufs:.1f} LUFS")
        else:
            notes.append(f"Loudness optimal: {integrated_lufs:.1f} LUFS (target: {timeline.audio.target_lufs:.1f} LUFS)")

        return RenderQAResult(
            output_path=output_path,
            duration=measured_duration,
            width=width,
            height=height,
            fps=fps_eval,
            integrated_lufs=integrated_lufs,
            file_size_bytes=file_size,
            render_time_seconds=render_time,
            passed=passed,
            notes=notes
        )


renderer = TimelineRenderer()
