import os
import subprocess
from pathlib import Path
from backend.app.core.config import settings
from backend.app.models.timeline import WordTimestamp
from backend.app.models.analysis import AnalysisReport, EditDecision, EditOperationType, AudioAnalysis, WordDetail
from backend.app.pipelines.edit_video.validator import cut_validator
from backend.app.pipelines.edit_video.compiler import edl_compiler
from backend.app.pipelines.edit_video.pipeline import auto_edit_pipeline
from backend.app.media.ffmpeg_wrapper import ffmpeg


def create_sample_raw_talking_head(output_mp4: str, duration: float = 6.0) -> str:
    """Create a sample talking-head test video with audio silences."""
    Path(output_mp4).parent.mkdir(parents=True, exist_ok=True)
    # Generate 6s video with 2 visual scene cuts and an audio silence gap
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=navy:s=1280x720:d={duration}",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2.0",
        "-f", "lavfi", "-i", "anullsrc=duration=2.0",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2.0",
        "-filter_complex", "[1:a][2:a][3:a]concat=n=3:v=0:a=1[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        output_mp4
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_mp4


def test_cut_validator_rules():
    # Build sample report with words and candidate cuts
    words = [
        WordDetail(word="প্রথম", start=0.2, end=0.8, is_filler=False),
        WordDetail(word="দ্বিতীয়", start=1.5, end=2.2, is_filler=False),
        WordDetail(word="মানে", start=3.0, end=3.4, is_filler=True)
    ]
    suggested = [
        # Bad cut overlapping first word mid-word (0.5 to 1.0)
        EditDecision(id="c1", operation=EditOperationType.CUT_SILENCE, start_time=0.5, end_time=1.2, reason="Silence"),
        # Valid filler cut
        EditDecision(id="c2", operation=EditOperationType.CUT_FILLER, start_time=3.0, end_time=3.4, reason="Filler")
    ]
    report = AnalysisReport(
        video_path="dummy.mp4",
        duration_seconds=5.0,
        width=1920,
        height=1080,
        fps=30.0,
        language="bn",
        transcript_text="প্রথম দ্বিতীয় মানে",
        words=words,
        audio=AudioAnalysis(integrated_lufs=-14.0, true_peak_db=-1.0),
        suggested_edits=suggested
    )

    valid_cuts = cut_validator.validate_and_repair_cuts(report, aggressiveness="balanced")

    # Assert cuts were repaired and don't cut inside 'প্রথম'
    for cut in valid_cuts:
        assert not (0.2 < cut.start_time < 0.8)


def test_edl_to_timeline_compiler():
    words = [
        WordDetail(word="স্বাগতম", start=0.5, end=1.0, is_filler=False),
        WordDetail(word="সবাইকে", start=1.1, end=1.8, is_filler=False),
        WordDetail(word="আজকে", start=3.5, end=4.2, is_filler=False)
    ]
    cuts = [
        # Cut 2.0s to 3.2s
        EditDecision(id="c1", operation=EditOperationType.CUT_SILENCE, start_time=2.0, end_time=3.2, reason="Cut gap")
    ]
    report = AnalysisReport(
        video_path="dummy.mp4",
        duration_seconds=5.0,
        width=1920,
        height=1080,
        fps=30.0,
        language="bn",
        transcript_text="স্বাগতম সবাইকে আজকে",
        words=words,
        audio=AudioAnalysis(integrated_lufs=-14.0, true_peak_db=-1.0),
        suggested_edits=cuts
    )

    timeline = edl_compiler.compile(
        original_video_path="dummy.mp4",
        report=report,
        validated_cuts=cuts,
        target_aspect_ratio="16:9",
        enable_punch_in_zooms=True
    )

    assert timeline.total_duration() < 5.0
    # Segments should be: (0.0 to 2.0) and (3.2 to 5.0) -> total 3.8s
    assert round(timeline.total_duration(), 1) == 3.8
    # Second clip should have punch-in zoom transform
    video_track = timeline.tracks[0]
    assert len(video_track.clips) == 2
    assert video_track.clips[1].transform is not None
    assert video_track.clips[1].transform.scale == 1.12


def test_auto_edit_pipeline_end_to_end():
    settings.init_directories()
    raw_vid = str(settings.data_dir / "test_raw_for_edit.mp4")
    create_sample_raw_talking_head(raw_vid, duration=6.0)

    out_edited = str(settings.data_dir / "test_renders" / "test_edited_output.mp4")

    res = auto_edit_pipeline.edit(
        video_path=raw_vid,
        project_id="test_edit_run",
        language="bn",
        goal="talking_head_polish",
        aggressiveness="balanced",
        target_aspect_ratio="16:9",
        enable_punch_zooms=True,
        add_captions=True,
        add_music_bed=False,
        output_path=out_edited
    )

    assert os.path.exists(out_edited)
    assert os.path.getsize(out_edited) > 10000

    comp = res["comparison"]
    assert comp["original_duration"] >= 5.8
    assert comp["edited_duration"] < comp["original_duration"]
    assert comp["time_saved_seconds"] > 0
    assert comp["punch_zooms_enabled"] is True

    qa = res["qa"]
    assert qa["passed"] is True
    assert qa["duration"] == comp["edited_duration"]

    # Verify media streams
    probe = ffmpeg.probe_media(out_edited)
    streams = probe.get("streams", [])
    assert any(s.get("codec_type") == "video" for s in streams)
    assert any(s.get("codec_type") == "audio" for s in streams)

    # Cleanup
    if os.path.exists(raw_vid):
        os.remove(raw_vid)
    if os.path.exists(out_edited):
        os.remove(out_edited)
