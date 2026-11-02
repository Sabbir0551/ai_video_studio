import os
import pytest
from pathlib import Path
from PIL import Image
from backend.app.core.config import settings
from backend.app.presets.manager import preset_manager
from backend.app.core.cost_tracker import CostAndAttributionTracker, CostItem, AttributionRecord
from backend.app.providers.image.mock_image_provider import MockImageGenProvider
from backend.app.models.brand import BrandKit, WatermarkPosition
from backend.app.media.thumbnail import thumbnail_generator
from backend.app.pipelines.create_video.pipeline import CreateVideoPipeline
from backend.app.providers.llm.mock_llm_provider import MockLLMProvider
from backend.app.providers.tts.mock_tts_provider import MockTTSProvider


def test_preset_manager():
    presets = preset_manager.list_presets()
    assert len(presets) >= 4
    names = [p.name for p in presets]
    assert "clean_corporate" in names
    assert "short_hype" in names
    assert "documentary" in names
    assert "news_flash" in names

    short_preset = preset_manager.get_preset("short_hype")
    assert short_preset.aspect_ratio == "9:16"
    assert short_preset.caption.highlight_active_word is True


def test_cost_tracker_and_budget_cap():
    tracker = CostAndAttributionTracker(max_job_budget_usd=2.0)
    tracker.record_cost(CostItem(
        service="llm",
        provider="openai",
        units=500,
        unit_name="tokens",
        cost_usd=0.015
    ))
    assert tracker.total_cost_usd() == 0.015

    # Should raise error when exceeding $2.0 budget
    with pytest.raises(PermissionError):
        tracker.record_cost(CostItem(
            service="videogen",
            provider="runway",
            units=1,
            unit_name="clips",
            cost_usd=5.0
        ))

    credits_out = str(settings.data_dir / "test_credits.txt")
    tracker.export_credits_file(credits_out)
    assert os.path.exists(credits_out)
    with open(credits_out, "r", encoding="utf-8") as f:
        content = f.read()
    assert "AI VIDEO STUDIO - CREDITS" in content
    if os.path.exists(credits_out):
        os.remove(credits_out)


def test_mock_image_provider():
    import asyncio
    provider = MockImageGenProvider()
    out_img = str(settings.data_dir / "test_img_gen.png")
    res = asyncio.run(provider.generate_or_source_image(
        query_or_prompt="Artificial Intelligence Brain Neural",
        output_path=out_img,
        width=1280,
        height=720
    ))
    assert os.path.exists(out_img)
    with Image.open(out_img) as im:
        assert im.size == (1280, 720)
    if os.path.exists(out_img):
        os.remove(out_img)


def test_thumbnail_and_seo_generator():
    settings.init_directories()
    # Create a tiny 1-second dummy video to test thumbnail extraction
    dummy_vid = str(settings.data_dir / "test_thumb_source.mp4")
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", dummy_vid
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    thumb_out = str(settings.data_dir / "test_thumb.jpg")
    thumbnail_generator.generate_thumbnail(
        video_path=dummy_vid,
        title_text="কৃত্রিম বুদ্ধিমত্তার সেরা চমক",
        output_image_path=thumb_out
    )

    assert os.path.exists(thumb_out)
    with Image.open(thumb_out) as im:
        assert im.size == (1280, 720)

    # Cleanup
    if os.path.exists(dummy_vid):
        os.remove(dummy_vid)
    if os.path.exists(thumb_out):
        os.remove(thumb_out)


def test_fast_preview_and_watermark_pipeline():
    pipeline = CreateVideoPipeline(
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider(),
        image_provider=MockImageGenProvider()
    )

    out_mp4 = str(settings.data_dir / "test_renders" / "test_preview_watermark.mp4")
    brand = BrandKit(
        logo_path="assets/brand/logo_watermark.png",
        watermark_position=WatermarkPosition.TOP_RIGHT,
        watermark_opacity=0.8
    )

    res = pipeline.run(
        project_id="test_preview_proj",
        topic_or_content="Fast Preview Technology",
        language="en",
        preset_name="clean_corporate",
        output_path=out_mp4,
        brand_kit=brand,
        preview_mode=True, # Fast preview mode
        generate_thumbnail=True
    )

    assert os.path.exists(out_mp4)
    qa = res["qa"]
    assert qa["passed"] is True
    assert qa["resolution"] == "960x540" # Verified preview resolution
    assert res.get("thumbnail_path") is not None
    assert res.get("credits_path") is not None

    # Cleanup
    if os.path.exists(out_mp4):
        os.remove(out_mp4)
    if res.get("thumbnail_path") and os.path.exists(res["thumbnail_path"]):
        os.remove(res["thumbnail_path"])
