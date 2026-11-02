import os
import pytest
from pathlib import Path
from PIL import Image

from backend.app.core.config import settings
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.providers.video_gen.base import VideoGenResult
from backend.app.providers.video_gen.procedural_motion_provider import ProceduralMotionVideoProvider
from backend.app.providers.video_gen.manager import get_video_gen_provider
from backend.app.pipelines.create_video.pipeline import CreateVideoPipeline
from backend.app.providers.llm.mock_llm_provider import MockLLMProvider
from backend.app.providers.tts.mock_tts_provider import MockTTSProvider
from backend.app.providers.image.mock_image_provider import MockImageGenProvider


def test_procedural_motion_video_provider(tmp_path):
    """Verify that 2.5D parallax motion engine transforms a keyframe image into a moving MP4."""
    # 1. Create dummy input keyframe
    img_path = str(tmp_path / "test_keyframe.png")
    img = Image.new("RGB", (1024, 576), (30, 41, 59))
    img.save(img_path)

    out_mp4 = str(tmp_path / "test_motion.mp4")
    provider = ProceduralMotionVideoProvider()

    import asyncio
    res = asyncio.run(provider.animate_image_to_video(
        image_path=img_path,
        motion_prompt="Slow cinematic camera dolly in over farm meadow with horse",
        duration=3.0,
        output_path=out_mp4,
        aspect_ratio="16:9",
        width=1024,
        height=576
    ))

    assert os.path.exists(out_mp4)
    assert res.duration_seconds == 3.0
    assert res.width == 1024
    assert res.height == 576

    # Verify output stream specs with ffprobe
    probe = ffmpeg.probe_media(out_mp4)
    streams = probe.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    assert v_stream is not None
    assert int(v_stream.get("width", 0)) == 1024
    assert int(v_stream.get("height", 0)) == 576
    assert float(probe.get("format", {}).get("duration", 0.0)) >= 2.8


def test_video_gen_manager_provider_selection():
    """Verify provider selection logic based on API keys."""
    prov_default = get_video_gen_provider()
    assert prov_default.name == "procedural-motion"

    prov_luma = get_video_gen_provider(luma_api_key="luma-mock-key-1234567890")
    assert prov_luma.name == "luma-dream-machine"

    prov_kling = get_video_gen_provider(kling_api_key="kling-mock-key-1234567890")
    assert prov_kling.name == "kling-ai"


def test_create_video_pipeline_with_video_motion(tmp_path):
    """Verify end-to-end pipeline execution with video motion enabled."""
    settings.init_directories()
    pipeline = CreateVideoPipeline(
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider(),
        image_provider=MockImageGenProvider(),
        video_gen_provider=ProceduralMotionVideoProvider()
    )

    out_mp4 = str(tmp_path / "pipeline_motion_test.mp4")
    res = pipeline.run(
        project_id="test_motion_proj",
        topic_or_content="3D Animated Farm Nursery Rhyme with Horse",
        language="en",
        aspect_ratio="16:9",
        preset_name="clean_corporate",
        output_path=out_mp4,
        preview_mode=True,
        enable_video_motion=True
    )

    assert os.path.exists(out_mp4)
    assert res["qa"]["passed"] is True
