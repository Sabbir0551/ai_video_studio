import os
from pathlib import Path
from backend.app.core.config import settings
from backend.app.providers.llm.mock_llm_provider import MockLLMProvider
from backend.app.providers.tts.mock_tts_provider import MockTTSProvider
from backend.app.pipelines.create_video.pipeline import CreateVideoPipeline
from backend.app.media.ffmpeg_wrapper import ffmpeg


def test_create_video_pipeline_bangla():
    settings.init_directories()
    pipeline = CreateVideoPipeline(
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider()
    )

    out_mp4 = str(settings.data_dir / "test_renders" / "test_bangla_pipeline.mp4")
    res = pipeline.run(
        project_id="test_pipeline_bn",
        topic_or_content="কৃত্রিম বুদ্ধিমত্তা ও ভবিষ্যৎ প্রযুক্তি",
        language="bn",
        aspect_ratio="16:9",
        target_duration=10.0,
        output_path=out_mp4
    )

    assert os.path.exists(out_mp4)
    assert os.path.getsize(out_mp4) > 10000

    qa = res["qa"]
    assert qa["passed"] is True
    assert qa["duration"] > 0
    assert qa["resolution"] == "1920x1080"

    # Check media streams
    probe = ffmpeg.probe_media(out_mp4)
    streams = probe.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    assert has_video is True
    assert has_audio is True

    # Cleanup test render
    if os.path.exists(out_mp4):
        os.remove(out_mp4)


def test_create_video_pipeline_english():
    settings.init_directories()
    pipeline = CreateVideoPipeline(
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider()
    )

    out_mp4 = str(settings.data_dir / "test_renders" / "test_english_pipeline.mp4")
    res = pipeline.run(
        project_id="test_pipeline_en",
        topic_or_content="Modern Artificial Intelligence Systems",
        language="en",
        aspect_ratio="16:9",
        target_duration=10.0,
        output_path=out_mp4
    )

    assert os.path.exists(out_mp4)
    assert os.path.getsize(out_mp4) > 10000

    qa = res["qa"]
    assert qa["passed"] is True
    assert qa["duration"] > 0

    # Cleanup test render
    if os.path.exists(out_mp4):
        os.remove(out_mp4)
