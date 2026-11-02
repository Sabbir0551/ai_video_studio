import os
import subprocess
from pathlib import Path
from backend.app.core.config import settings
from backend.app.models.timeline import WordTimestamp
from backend.app.models.analysis import EditOperationType
from backend.app.analysis.ingest import video_ingestor
from backend.app.analysis.speech_analyzer import speech_analyzer
from backend.app.analysis.audio_analyzer import audio_quality_analyzer
from backend.app.analysis.visual_analyzer import visual_scene_analyzer
from backend.app.analysis.analyzer import multimodal_analyzer
from backend.app.providers.asr.mock_asr_provider import MockASRProvider


def create_sample_raw_video(output_mp4: str, duration: float = 6.0) -> str:
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


def test_video_ingestor():
    settings.init_directories()
    raw_vid = str(settings.data_dir / "test_raw_ingest.mp4")
    create_sample_raw_video(raw_vid, duration=4.0)

    work_dir = str(settings.data_dir / "test_ingest_work")
    res = video_ingestor.ingest(raw_vid, work_dir)

    assert os.path.exists(res.proxy_video_path)
    assert os.path.exists(res.audio_wav_path)
    assert res.duration >= 3.8
    assert res.width == 1280
    assert res.height == 720

    # Cleanup
    if os.path.exists(raw_vid):
        os.remove(raw_vid)
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)


def test_speech_analyzer_fillers_and_pauses():
    # Test Bengali filler word and pause detection
    words_bn = [
        WordTimestamp(word="আমি", start=0.2, end=0.6),
        WordTimestamp(word="আমি", start=0.65, end=0.9),       # Repeated stutter
        WordTimestamp(word="মানে", start=1.8, end=2.2),      # Filler word after 0.9s pause
        WordTimestamp(word="প্রযুক্তি", start=2.3, end=2.8),
        WordTimestamp(word="আসলে", start=4.0, end=4.4),      # Filler word after 1.2s pause
        WordTimestamp(word="দারুণ", start=4.5, end=5.0)
    ]

    detailed_words, edits, wpm = speech_analyzer.analyze_words(words_bn, language="bn")

    assert len(detailed_words) == 6
    fillers = [w for w in detailed_words if w.is_filler]
    assert len(fillers) == 2  # 'মানে' and 'আসলে'
    assert any(e.operation == EditOperationType.CUT_FILLER for e in edits)
    assert any(e.operation == EditOperationType.CUT_SILENCE for e in edits)
    assert wpm > 0


def test_audio_quality_analyzer():
    settings.init_directories()
    raw_vid = str(settings.data_dir / "test_raw_audio.mp4")
    create_sample_raw_video(raw_vid, duration=6.0)

    work_dir = str(settings.data_dir / "test_audio_work")
    ingest_res = video_ingestor.ingest(raw_vid, work_dir)

    audio_res = audio_quality_analyzer.analyze_audio(ingest_res.audio_wav_path)

    assert audio_res.integrated_lufs < 0
    # Our test video has a 2.0s silence gap in the middle
    assert len(audio_res.silence_segments) >= 1
    silence = audio_res.silence_segments[0]
    assert 1.5 <= silence[0] <= 2.5 # Silence starts around 2.0s

    # Cleanup
    if os.path.exists(raw_vid):
        os.remove(raw_vid)
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)


def test_visual_scene_analyzer():
    settings.init_directories()
    raw_vid = str(settings.data_dir / "test_raw_visual.mp4")
    create_sample_raw_video(raw_vid, duration=4.0)

    kf_dir = str(settings.data_dir / "test_keyframes")
    shots = visual_scene_analyzer.analyze_scenes(raw_vid, kf_dir, total_duration=4.0)

    assert len(shots) >= 1
    assert shots[0].keyframe_path is not None
    assert os.path.exists(shots[0].keyframe_path)

    # Test frame quality check
    quality = visual_scene_analyzer.evaluate_frame_quality(shots[0].keyframe_path)
    assert "mean_brightness" in quality

    # Cleanup
    if os.path.exists(raw_vid):
        os.remove(raw_vid)
    import shutil
    shutil.rmtree(kf_dir, ignore_errors=True)


def test_multimodal_analyzer_end_to_end():
    settings.init_directories()
    raw_vid = str(settings.data_dir / "test_raw_talking_head.mp4")
    create_sample_raw_video(raw_vid, duration=6.0)

    report = multimodal_analyzer.analyze(
        video_path=raw_vid,
        project_id="test_analyze_proj",
        language="bn",
        goal="talking_head_polish"
    )

    assert report.duration_seconds >= 5.8
    assert report.width == 1280
    assert report.height == 720
    assert len(report.words) > 0
    assert len(report.suggested_edits) > 0
    assert "Video Analysis Summary" in report.summary

    # Verify JSON output was written
    report_file = settings.data_dir / "projects" / "test_analyze_proj" / "analysis" / "analysis_report.json"
    assert report_file.exists()

    # Cleanup
    if os.path.exists(raw_vid):
        os.remove(raw_vid)
