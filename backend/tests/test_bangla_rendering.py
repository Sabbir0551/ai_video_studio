import os
from pathlib import Path
from PIL import Image
from backend.app.core.config import settings
from backend.app.media.bangla_shaper import (
    bangla_int_to_words,
    normalize_bangla_text_for_speech,
    generate_ass_subtitle_file
)
from backend.app.media.ffmpeg_wrapper import ffmpeg
from backend.app.models.timeline import CaptionItem, WordTimestamp


def test_bangla_number_normalization():
    assert bangla_int_to_words(0) == "শূন্য"
    assert bangla_int_to_words(5) == "পাঁচ"
    assert bangla_int_to_words(25) == "পঁচিশ"
    assert bangla_int_to_words(2026) == "দুই হাজার ছাব্বিশ"
    assert bangla_int_to_words(1200) == "এক হাজার দুই শত"


def test_bangla_text_speech_normalization():
    raw_text = "২০২৬ সালে ডা. রহিম ১২০০ টাকা দিয়ে ৫% ডিসকাউন্ট পান।"
    normalized = normalize_bangla_text_for_speech(raw_text)
    assert "দুই হাজার ছাব্বিশ" in normalized
    assert "ডাক্তার" in normalized
    assert "টাকা" in normalized
    assert "শতাংশ" in normalized


def test_bangla_harfbuzz_frame_render():
    """Verify that FFmpeg libass renders complex Bengali conjuncts properly without crashes."""
    settings.init_directories()
    out_ass = str(settings.data_dir / "test_shaping.ass")
    out_png = str(settings.data_dir / "test_shaping.png")

    complex_bangla = "বিজ্ঞান, প্রযুক্তি, স্বাস্থ্য ও শৃঙ্খলা — ক্ষ, জ্ঞ, ষ্ণ, ঙ্ক, ঙ্গ।"
    caption = CaptionItem(
        id="c_test",
        start=0.0,
        end=2.0,
        text=complex_bangla,
        words=[
            WordTimestamp(word="বিজ্ঞান,", start=0.0, end=0.4),
            WordTimestamp(word="প্রযুক্তি,", start=0.4, end=0.8),
            WordTimestamp(word="স্বাস্থ্য", start=0.8, end=1.4),
            WordTimestamp(word="শৃঙ্খলা", start=1.4, end=2.0)
        ]
    )

    generate_ass_subtitle_file(
        captions=[caption],
        output_path=out_ass,
        font_name="Noto Sans Bengali",
        font_size=56,
        play_res_x=1920,
        play_res_y=1080,
        highlight_active_word=True
    )

    rendered = ffmpeg.render_color_frame_with_ass(
        ass_path=out_ass,
        output_png=out_png,
        fonts_dir=str(settings.fonts_dir),
        width=1920,
        height=1080
    )

    assert rendered is True
    assert os.path.exists(out_png)

    # Validate image dimensions and pixel content
    im = Image.open(out_png)
    assert im.size == (1920, 1080)
    extrema = im.getextrema()
    # Image should have white/colored text pixels and not be completely blank
    assert extrema[0][1] > 0
    assert extrema[1][1] > 0

    # Cleanup artifacts
    if os.path.exists(out_ass):
        os.remove(out_ass)
    if os.path.exists(out_png):
        os.remove(out_png)
