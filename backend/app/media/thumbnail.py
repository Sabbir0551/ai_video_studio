import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.timeline import Timeline


class ThumbnailAndMetadataGenerator:
    """Generates high-CTR thumbnail images and SEO titles, descriptions, hashtags and chapters."""

    def generate_thumbnail(
        self,
        video_path: str,
        title_text: str,
        output_image_path: str,
        timestamp_seconds: float = 1.0,
        font_path: Optional[str] = None
    ) -> str:
        Path(output_image_path).parent.mkdir(parents=True, exist_ok=True)
        temp_frame = str(Path(output_image_path).parent / "temp_keyframe.png")

        # 1. Extract frame using FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp_seconds),
            "-i", video_path,
            "-frames:v", "1",
            temp_frame
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(temp_frame):
            # Fallback to frame 0.0s if timestamp exceeds video
            fallback_cmd = [
                "ffmpeg", "-y",
                "-ss", "0.0",
                "-i", video_path,
                "-frames:v", "1",
                temp_frame
            ]
            subprocess.run(fallback_cmd, capture_output=True, check=True)

        # 2. Open frame and apply thumbnail graphics
        img = Image.open(temp_frame).convert("RGBA")
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Bottom-third dark gradient for contrast
        gradient_h = int(h * 0.45)
        for y in range(gradient_h):
            alpha = int((y / gradient_h) * 210)
            draw.line([(0, h - gradient_h + y), (w, h - gradient_h + y)], fill=(10, 15, 29, alpha))

        # Accent border badge
        draw.rectangle([0, h - 12, w, h], fill=(234, 179, 8, 255)) # Yellow border

        # Compose overlay onto base frame
        composed = Image.alpha_composite(img, overlay).convert("RGB")

        # 3. Draw Bengali / English Title Text
        font_file = font_path or str(settings.default_font_path)
        draw_composed = ImageDraw.Draw(composed)
        
        font_size = int(h * 0.075)
        try:
            font = ImageFont.truetype(font_file, font_size)
        except Exception:
            font = ImageFont.load_default()

        # Split text into lines if long
        words = title_text.split()
        lines = []
        cur_line = []
        for word in words:
            if len(" ".join(cur_line + [word])) > 28:
                lines.append(" ".join(cur_line))
                cur_line = [word]
            else:
                cur_line.append(word)
        if cur_line:
            lines.append(" ".join(cur_line))

        text_y = int(h * 0.65)
        for line in lines[:2]: # Max 2 punchy lines
            # Black outline
            for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 3), (0, -3), (3, 0), (-3, 0)]:
                draw_composed.text((60 + dx, text_y + dy), line, font=font, fill=(0, 0, 0))
            # Bright yellow/white text
            draw_composed.text((60, text_y), line, font=font, fill=(255, 235, 59))
            text_y += int(font_size * 1.3)

        composed.save(output_image_path, "JPEG", quality=95)

        # Clean temp frame
        if os.path.exists(temp_frame):
            os.remove(temp_frame)

        logger.info(f"Generated thumbnail: {output_image_path}")
        return output_image_path

    def generate_seo_metadata(self, timeline: Timeline, topic: str, language: str = "bn") -> Dict[str, Any]:
        """Generate platform titles, description, hashtags, and timestamped chapters."""
        is_bn = language.startswith("bn")
        
        # Calculate chapters from captions or visual clips
        chapters = ["00:00 " + ("ভূমিকা" if is_bn else "Introduction")]
        cumulative_time = 0.0
        
        for idx, track in enumerate(timeline.tracks):
            if track.track_type.value == "voice":
                for c_idx, clip in enumerate(track.clips):
                    if clip.timeline_start > 0.5:
                        mins = int(clip.timeline_start // 60)
                        secs = int(clip.timeline_start % 60)
                        label = f"দৃশ্য {c_idx+1}" if is_bn else f"Part {c_idx+1}"
                        chapters.append(f"{mins:02d}:{secs:02d} {label}")
                break

        title_candidates = [
            f"{topic}: যা আপনার জানা প্রয়োজন" if is_bn else f"{topic}: Everything You Need to Know",
            f"১ মিনিটে শিখুন {topic}" if is_bn else f"Learn {topic} in 60 Seconds",
            f"{topic} নিয়ে নতুন চমক!" if is_bn else f"The Truth About {topic}"
        ]

        hashtags = ["#AI", "#Technology", "#Explainer", "#Trending"]
        if is_bn:
            hashtags.extend(["#বাংলা", "#প্রযুক্তি", "#শিক্ষা"])

        description = (
            f"{topic}\n\n"
            f"{'এই ভিডিওতে সহজ ভাষায় আলোচনা করা হয়েছে।' if is_bn else 'In this video, we break down the concepts clearly and concisely.'}\n\n"
            f"টাইমকোড (Chapters):\n" + "\n".join(chapters) + "\n\n"
            + " ".join(hashtags)
        )

        return {
            "title_candidates": title_candidates,
            "description": description,
            "hashtags": hashtags,
            "chapters": chapters
        }


thumbnail_generator = ThumbnailAndMetadataGenerator()
