from typing import List, Optional, Tuple, Dict, Any
from backend.app.models.timeline import (
    Timeline,
    CanvasConfig,
    AudioConfig,
    Track,
    Clip,
    TrackType,
    CaptionItem,
    WordTimestamp,
    Transform,
    SidechainDucking
)
from backend.app.models.analysis import AnalysisReport, EditDecision, WordDetail
from backend.app.core.config import settings
from backend.app.core.logging import logger


class EDLToTimelineCompiler:
    """Compiles an Edit Decision List (EDL) and AnalysisReport into a fully executable Canonical Timeline."""

    def compile(
        self,
        original_video_path: str,
        report: AnalysisReport,
        validated_cuts: List[EditDecision],
        target_aspect_ratio: str = "16:9",
        enable_punch_in_zooms: bool = True,
        add_captions: bool = True,
        add_music_bed: bool = True
    ) -> Timeline:
        logger.info(f"Compiling EDL to Timeline [cuts={len(validated_cuts)}, aspect={target_aspect_ratio}, punch_zooms={enable_punch_in_zooms}]")

        total_video_duration = report.duration_seconds
        sorted_cuts = sorted(validated_cuts, key=lambda x: x.start_time)

        # 1. Invert cuts into kept intervals: [(start, end), ...]
        kept_intervals: List[Tuple[float, float]] = []
        cursor = 0.0

        for cut in sorted_cuts:
            if cut.start_time > cursor + 0.1:
                kept_intervals.append((cursor, cut.start_time))
            cursor = max(cursor, cut.end_time)

        if cursor < total_video_duration - 0.1:
            kept_intervals.append((cursor, total_video_duration))

        # If no cuts were made, keep entire video
        if not kept_intervals:
            kept_intervals = [(0.0, total_video_duration)]

        # 2. Build Video Track with alternating punch-in zooms
        width, height = (1080, 1920) if target_aspect_ratio == "9:16" else (1920, 1080)
        video_clips: List[Clip] = []
        timeline_time = 0.0
        zoom_state = False

        for idx, (seg_start, seg_end) in enumerate(kept_intervals):
            dur = seg_end - seg_start
            transform = None

            if enable_punch_in_zooms and idx > 0:
                zoom_state = not zoom_state
                if zoom_state:
                    transform = Transform(scale=1.12) # 112% punch-in zoom

            video_clips.append(Clip(
                id=f"clip_seg_{idx+1:03d}",
                source_path=original_video_path,
                source_in=round(seg_start, 3),
                source_out=round(seg_end, 3),
                timeline_start=round(timeline_time, 3),
                timeline_end=round(timeline_time + dur, 3),
                speed=1.0,
                volume=1.0,
                transform=transform
            ))
            timeline_time += dur

        total_edited_duration = timeline_time
        video_track = Track(
            id="track_edited_video",
            name="Edited Video Track",
            track_type=TrackType.VIDEO,
            z_index=0,
            clips=video_clips
        )

        tracks_list = [video_track]

        # 3. Add background music bed with ducking if requested
        music_file = str(settings.assets_dir / "audio" / "ambient_music.mp3")
        import os
        if add_music_bed and os.path.exists(music_file):
            tracks_list.append(Track(
                id="track_bg_music",
                name="Ambient Music Bed",
                track_type=TrackType.MUSIC,
                z_index=1,
                clips=[
                    Clip(
                        id="music_edit_01",
                        source_path=music_file,
                        source_in=0.0,
                        source_out=total_edited_duration,
                        timeline_start=0.0,
                        timeline_end=total_edited_duration,
                        volume=0.14,
                        sidechain_ducking=SidechainDucking(
                            source_track_id="track_edited_video",
                            threshold_db=-24.0,
                            reduction_db=-12.0
                        )
                    )
                ]
            ))

        # 4. Map surviving words to new edited timeline timestamps
        compiled_captions: List[CaptionItem] = []
        if add_captions and report.words:
            surviving_words: List[WordTimestamp] = []
            for w in report.words:
                if w.is_filler:
                    continue
                # Check if word falls inside any kept interval
                for seg_idx, (s_start, s_end) in enumerate(kept_intervals):
                    if s_start <= w.start and w.end <= s_end:
                        # Calculate timeline offset for this segment
                        seg_tl_start = video_clips[seg_idx].timeline_start
                        word_tl_start = seg_tl_start + (w.start - s_start)
                        word_tl_end = seg_tl_start + (w.end - s_start)
                        surviving_words.append(WordTimestamp(
                            word=w.word,
                            start=round(word_tl_start, 3),
                            end=round(word_tl_end, 3)
                        ))
                        break

            # Group surviving words into caption phrases (e.g. 4-6 words per caption card)
            chunk_size = 5
            for i in range(0, len(surviving_words), chunk_size):
                chunk = surviving_words[i:i + chunk_size]
                if chunk:
                    compiled_captions.append(CaptionItem(
                        id=f"cap_edit_{i//chunk_size + 1}",
                        start=chunk[0].start,
                        end=chunk[-1].end,
                        text=" ".join(cw.word for cw in chunk),
                        words=chunk,
                        style="tiktok_highlight"
                    ))

        timeline = Timeline(
            project_id=f"edit_{report.language}",
            canvas=CanvasConfig(
                width=width,
                height=height,
                aspect_ratio=target_aspect_ratio,
                fps=report.fps
            ),
            audio=AudioConfig(
                sample_rate=48000,
                channels=2,
                target_lufs=settings.default_lufs_target,
                true_peak=settings.default_true_peak_target
            ),
            tracks=tracks_list,
            captions=compiled_captions,
            metadata={
                "original_video": original_video_path,
                "original_duration": report.duration_seconds,
                "edited_duration": round(total_edited_duration, 2),
                "cuts_count": len(sorted_cuts),
                "punch_zooms_enabled": enable_punch_in_zooms
            }
        )

        logger.info(f"EDL compiled: Original {total_video_duration:.2f}s -> Edited {total_edited_duration:.2f}s ({len(video_clips)} segments)")
        return timeline


edl_compiler = EDLToTimelineCompiler()
