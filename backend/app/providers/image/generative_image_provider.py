import os
import re
import math
import httpx
import urllib.parse
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.providers.image.base import ImageGenProvider, ImageGenResult


class GenerativeImageProvider(ImageGenProvider):
    """
    High-fidelity Generative AI Image Provider.
    - Generates 3D Pixar, Disney, photorealistic, and cinematic character/scene visuals.
    - Connects directly to OpenAI DALL-E 3 (if OPENAI_API_KEY is configured).
    - Uses Pollinations AI (with Pollen key if available, or free tier with rate-limit mitigation).
    - Robust failover to dynamic scene-specific 3D cartoon vector illustration if offline or rate-limited.
    """

    def __init__(self, default_seed: Optional[int] = None):
        self._default_seed = default_seed or 42891

    @property
    def name(self) -> str:
        return "generative-ai"

    def _extract_character_and_seed(self, prompt: str, scene_number: Optional[int] = None) -> int:
        """Derive a consistent, unique integer seed per character and scene."""
        p_lower = prompt.lower()
        if "puppy" in p_lower or "dog" in p_lower or "কুকুর" in p_lower:
            base = 10101
        elif "kitten" in p_lower or "cat" in p_lower or "বিড়াল" in p_lower or "বিড়াল" in p_lower:
            base = 20202
        elif "duckling" in p_lower or "duck" in p_lower or "হাঁস" in p_lower or "buli" in p_lower:
            base = 30303
        elif "lamb" in p_lower or "sheep" in p_lower or "ভেড়া" in p_lower or "ভেড়া" in p_lower:
            base = 40404
        elif "pony" in p_lower or "horse" in p_lower or "foal" in p_lower or "ঘোড়া" in p_lower:
            base = 50505
        elif "cow" in p_lower or "গরু" in p_lower:
            base = 60606
        elif "rainbow" in p_lower or "রামধনু" in p_lower or "রংধনু" in p_lower:
            base = 70707
        else:
            char_match = re.search(r"character\s*:\s*([^,\.\n]+)", prompt, re.IGNORECASE)
            if char_match:
                base = abs(hash(char_match.group(1).strip().lower())) % 999999
            else:
                base = self._default_seed

        sc_num = scene_number or 1
        sc_match = re.search(r"scene\s*(\d+)", prompt, re.IGNORECASE)
        if sc_match:
            sc_num = int(sc_match.group(1))

        return (base + sc_num * 1337) % 999999

    async def _generate_openai(
        self,
        prompt: str,
        output_path: str,
        width: int,
        height: int,
        api_key: str
    ) -> bool:
        """Generate high-fidelity 3D Pixar imagery via OpenAI DALL-E 3."""
        try:
            url = "https://api.openai.com/v1/images/generations"
            size = "1024x1024" if width == height else ("1024x1792" if height > width else "1792x1024")
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": "standard",
                "response_format": "url"
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    img_url = res.json()["data"][0]["url"]
                    img_resp = await client.get(img_url)
                    with open(output_path, "wb") as f:
                        f.write(img_resp.content)
                    with Image.open(output_path) as im:
                        if im.size != (width, height):
                            im_resized = im.resize((width, height), Image.Resampling.LANCZOS)
                            im_resized.save(output_path, "JPEG", quality=95)
                    logger.info(f"Generated DALL-E 3 visual -> {output_path}")
                    return True
        except Exception as e:
            logger.warning(f"OpenAI image generation error: {e}")
        return False

    async def generate_or_source_image(
        self,
        query_or_prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        scene_number: Optional[int] = None,
        scene_seed: Optional[int] = None,
        **kwargs
    ) -> ImageGenResult:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        seed = scene_seed or self._extract_character_and_seed(query_or_prompt, scene_number=scene_number)

        clean_prompt = re.sub(r'[\*\#\_\"\'\`]', '', query_or_prompt)
        clean_prompt = re.sub(r'\s+', ' ', clean_prompt).strip()
        if len(clean_prompt) > 450:
            clean_prompt = clean_prompt[:450]

        generated_via_api = False

        # 1. Try OpenAI if API key configured
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", None)
        if openai_key and len(openai_key) > 10:
            generated_via_api = await self._generate_openai(
                clean_prompt, output_path, width, height, openai_key
            )

        # 2. Try Pollinations AI with rate-limit handling
        if not generated_via_api:
            req_w = 1024 if width >= height else 576
            req_h = 576 if width >= height else 1024
            encoded = urllib.parse.quote(clean_prompt)

            pollen_key = os.getenv("POLLEN_API_KEY") or os.getenv("POLLINATIONS_API_KEY")
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={req_w}&height={req_h}&seed={seed}&nologo=true"
            if pollen_key:
                url += f"&key={pollen_key}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            try:
                async with httpx.AsyncClient(timeout=35.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        temp_load = output_path + ".tmp"
                        with open(temp_load, "wb") as f:
                            f.write(resp.content)

                        with Image.open(temp_load) as img:
                            img_rgb = img.convert("RGB")
                            if img_rgb.size != (width, height):
                                final_img = img_rgb.resize((width, height), Image.Resampling.LANCZOS)
                            else:
                                final_img = img_rgb
                            final_img.save(output_path, "JPEG", quality=95)

                        try:
                            os.remove(temp_load)
                        except Exception:
                            pass

                        generated_via_api = True
                        logger.info(f"Generated AI character visual (seed={seed}) for: '{clean_prompt[:50]}...' -> {output_path}")
                    elif resp.status_code == 402:
                        logger.warning("Pollinations rate limit reached (1 image every 45s without key). Activating dynamic rich vector illustrator.")
                    else:
                        logger.warning(f"Pollinations returned status {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                logger.warning(f"Generative API request failed ({type(e).__name__}: {e})")

        # 3. Dynamic Scene-Specific Fallback Illustrator
        if not generated_via_api:
            self._render_rich_illustrated_fallback(
                prompt=clean_prompt,
                output_path=output_path,
                width=width,
                height=height,
                seed=seed
            )

        return ImageGenResult(
            image_path=output_path,
            width=width,
            height=height,
            provider_name=self.name if generated_via_api else "rich-illustration-engine",
            license_type="CC0 / AI Generated",
            attribution="Generated by AI Video Studio Generative Engine",
            cost_usd=0.0
        )

    def _render_rich_illustrated_fallback(
        self,
        prompt: str,
        output_path: str,
        width: int,
        height: int,
        seed: int
    ) -> None:
        """Render a vibrant, multi-layered 3D storybook illustration dynamically matching the scene characters and weather."""
        p_lower = prompt.lower()
        is_night = any(w in p_lower for w in ["night", "stars", "sleep", "moon", "রাত"])
        is_sunset = any(w in p_lower for w in ["sunset", "dusk", "orange", "pink", "evening", "সন্ধ্যা"])
        is_rain = any(w in p_lower for w in ["rain", "cloud", "storm", "gray", "grey", "বৃষ্টি", "মেঘ"])
        is_rainbow = any(w in p_lower for w in ["rainbow", "রামধনু", "রংধনু", "yay", "sunshine"])

        # Character detection
        is_puppy = any(w in p_lower for w in ["puppy", "dog", "কুকুর"])
        is_kitten = any(w in p_lower for w in ["kitten", "kitty", "cat", "বিড়াল", "বিড়াল"])
        is_duck = any(w in p_lower for w in ["duck", "duckling", "হাঁস", "buli"])
        is_lamb = any(w in p_lower for w in ["lamb", "sheep", "ভেড়া", "ভেড়া"])
        is_pony = any(w in p_lower for w in ["horse", "pony", "foal", "ঘোড়া", "ঘোড়া", "cow", "গরু"])
        is_farm = any(w in p_lower for w in ["farm", "barn", "stable", "hay", "আস্তাবল"]) or is_pony

        img = Image.new("RGB", (width, height), (135, 206, 235))
        draw = ImageDraw.Draw(img)

        # 1. Sky Gradient
        if is_night:
            top_sky = (15, 23, 42)
            bottom_sky = (30, 41, 59)
        elif is_sunset:
            top_sky = (124, 45, 18)
            bottom_sky = (249, 115, 22)
        elif is_rain and not is_rainbow:
            top_sky = (71, 85, 105)
            bottom_sky = (148, 163, 184)
        else:
            top_sky = (56, 189, 248)
            bottom_sky = (224, 242, 254)

        for y in range(int(height * 0.7)):
            ratio = y / (height * 0.7)
            r = int(top_sky[0] + ratio * (bottom_sky[0] - top_sky[0]))
            g = int(top_sky[1] + ratio * (bottom_sky[1] - top_sky[1]))
            b = int(top_sky[2] + ratio * (bottom_sky[2] - top_sky[2]))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Celestial Body (Sun/Moon/Clouds/Rainbow)
        sun_x = int(width * 0.8)
        sun_y = int(height * 0.22)
        sun_r = int(min(width, height) * 0.1)

        if is_night:
            draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(254, 240, 138))
            draw.ellipse([sun_x - sun_r + 20, sun_y - sun_r - 10, sun_x + sun_r + 20, sun_y + sun_r - 10], fill=(bottom_sky[0], bottom_sky[1], bottom_sky[2]))
            for i in range(30):
                sx = int((seed * 37 + i * 137) % (width * 0.9))
                sy = int((seed * 19 + i * 83) % (height * 0.5))
                draw.ellipse([sx, sy, sx + 4, sy + 4], fill=(255, 255, 255))
        elif is_rainbow:
            # Spectacular 7-color arching rainbow
            colors = [
                (239, 68, 68),   # Red
                (249, 115, 22),  # Orange
                (250, 204, 21),  # Yellow
                (34, 197, 94),   # Green
                (6, 182, 212),   # Cyan
                (59, 130, 246),  # Blue
                (168, 85, 247)   # Violet
            ]
            rb_cx = int(width * 0.5)
            rb_cy = int(height * 0.75)
            base_r = int(min(width, height) * 0.55)
            for idx, c in enumerate(colors):
                cur_r = base_r - idx * 12
                draw.arc([rb_cx - cur_r, rb_cy - cur_r, rb_cx + cur_r, rb_cy + cur_r], start=180, end=0, fill=c, width=12)

            # Golden smiling sun
            draw.ellipse([sun_x - sun_r - 20, sun_y - sun_r - 20, sun_x + sun_r + 20, sun_y + sun_r + 20], fill=(254, 215, 170))
            draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(251, 191, 36))
        elif is_rain:
            # Dramatic fluffy rain clouds
            for cx in [int(width * 0.25), int(width * 0.5), int(width * 0.75)]:
                cy = int(height * 0.18)
                draw.ellipse([cx - 100, cy - 45, cx + 100, cy + 45], fill=(100, 116, 139))
                draw.ellipse([cx - 55, cy - 80, cx + 55, cy + 15], fill=(100, 116, 139))
            # Diagonal falling rain streaks
            for i in range(50):
                rx = int((seed * 23 + i * 97) % width)
                ry = int((seed * 41 + i * 67) % (height * 0.7))
                draw.line([(rx, ry), (rx - 5, ry + 22)], fill=(186, 230, 253), width=2)
        else:
            draw.ellipse([sun_x - sun_r - 15, sun_y - sun_r - 15, sun_x + sun_r + 15, sun_y + sun_r + 15], fill=(254, 215, 170))
            draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(251, 191, 36))

        # 3. Ground / Lush Meadow & Rolling Hills
        ground_y = int(height * 0.65)
        hill_bg = (34, 197, 94) if not is_night else (20, 83, 45)
        draw.chord([-100, ground_y - 80, int(width * 0.7), height + 100], start=180, end=0, fill=hill_bg)
        hill_fg = (22, 163, 74) if not is_night else (22, 101, 52)
        draw.chord([int(width * 0.3), ground_y - 60, width + 200, height + 100], start=180, end=0, fill=hill_fg)
        draw.rectangle([0, ground_y + 40, width, height], fill=hill_fg)

        # Draw water puddles if rain
        if is_rain or is_rainbow:
            puddle_x = int(width * 0.65)
            puddle_y = ground_y + 60
            draw.ellipse([puddle_x - 80, puddle_y - 20, puddle_x + 80, puddle_y + 20], fill=(125, 211, 252))
            draw.ellipse([puddle_x - 50, puddle_y - 10, puddle_x + 50, puddle_y + 10], fill=(186, 230, 253))

        # 4. Contextual Red Barn & Fence
        if is_farm:
            bx = int(width * 0.08)
            bw = int(width * 0.32)
            bh = int(height * 0.28)
            by = ground_y - bh + 40
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(185, 28, 28))
            draw.polygon([
                (bx - 20, by),
                (bx + int(bw * 0.2), by - 55),
                (bx + int(bw * 0.5), by - 85),
                (bx + int(bw * 0.8), by - 55),
                (bx + bw + 20, by)
            ], fill=(220, 38, 38))
            door_w = int(bw * 0.35)
            door_h = int(bh * 0.55)
            dx = bx + int(bw * 0.32)
            dy = by + bh - door_h
            draw.rectangle([dx, dy, dx + door_w, dy + door_h], fill=(254, 242, 242))
            draw.line([(dx, dy), (dx + door_w, dy + door_h)], fill=(185, 28, 28), width=3)
            draw.line([(dx + door_w, dy), (dx, dy + door_h)], fill=(185, 28, 28), width=3)

        # 5. Distinct Character Renderings (3D Cartoon Style)
        cx = int(width * 0.5 if not is_farm else width * 0.58)
        cy = ground_y

        if is_puppy:
            # Cute 3D Golden Puppy Dog with Floppy Ears & Yellow Raincoat
            px, py = cx, cy + 15
            # Body with raincoat
            draw.ellipse([px - 45, py - 35, px + 45, py + 40], fill=(250, 204, 21))
            # Head
            draw.ellipse([px - 40, py - 95, px + 40, py - 25], fill=(217, 119, 6))
            # Floppy Ears
            draw.ellipse([px - 58, py - 90, px - 32, py - 35], fill=(180, 83, 9))
            draw.ellipse([px + 32, py - 90, px + 58, py - 35], fill=(180, 83, 9))
            # Cute big eyes with catchlights
            draw.ellipse([px - 22, py - 70, px - 6, py - 52], fill=(15, 23, 42))
            draw.ellipse([px + 6, py - 70, px + 22, py - 52], fill=(15, 23, 42))
            draw.ellipse([px - 18, py - 68, px - 10, py - 60], fill=(255, 255, 255))
            draw.ellipse([px + 10, py - 68, px + 18, py - 60], fill=(255, 255, 255))
            # Muzzle & Button Nose
            draw.ellipse([px - 15, py - 55, px + 15, py - 35], fill=(254, 243, 199))
            draw.ellipse([px - 8, py - 54, px + 8, py - 42], fill=(15, 23, 42))
            draw.arc([px - 10, py - 46, px + 10, py - 36], start=0, end=180, fill=(180, 83, 9), width=2)
            # Yellow Rain Boots
            draw.rectangle([px - 32, py + 35, px - 12, py + 55], fill=(234, 179, 8))
            draw.rectangle([px + 12, py + 35, px + 32, py + 55], fill=(234, 179, 8))

        elif is_kitten:
            # Cute 3D Fluffy White Kitten with Pink Nose & Red Umbrella
            kx, ky = cx, cy + 15
            # Body
            draw.ellipse([kx - 40, ky - 30, kx + 40, ky + 40], fill=(248, 250, 252))
            # Head
            draw.ellipse([kx - 38, ky - 90, kx + 38, ky - 22], fill=(255, 255, 255))
            # Pointy Cat Ears
            draw.polygon([(kx - 35, ky - 80), (kx - 22, ky - 110), (kx - 8, ky - 85)], fill=(248, 250, 252))
            draw.polygon([(kx - 30, ky - 82), (kx - 22, ky - 102), (kx - 12, ky - 85)], fill=(244, 114, 182))
            draw.polygon([(kx + 8, ky - 85), (kx + 22, ky - 110), (kx + 35, ky - 80)], fill=(248, 250, 252))
            draw.polygon([(kx + 12, ky - 85), (kx + 22, ky - 102), (kx + 30, ky - 82)], fill=(244, 114, 182))
            # Big blue cartoon eyes
            draw.ellipse([kx - 22, ky - 66, kx - 6, ky - 48], fill=(59, 130, 246))
            draw.ellipse([kx + 6, ky - 66, kx + 22, ky - 48], fill=(59, 130, 246))
            draw.ellipse([kx - 18, ky - 64, kx - 10, ky - 56], fill=(255, 255, 255))
            draw.ellipse([kx + 10, ky - 64, kx + 18, ky - 56], fill=(255, 255, 255))
            # Pink Nose & Whiskers
            draw.polygon([(kx - 6, ky - 48), (kx + 6, ky - 48), (kx, ky - 42)], fill=(244, 114, 182))
            draw.line([(kx - 15, ky - 46), (kx - 35, ky - 50)], fill=(148, 163, 184), width=2)
            draw.line([(kx - 15, ky - 42), (kx - 35, ky - 42)], fill=(148, 163, 184), width=2)
            draw.line([(kx + 15, ky - 46), (kx + 35, ky - 50)], fill=(148, 163, 184), width=2)
            draw.line([(kx + 15, ky - 42), (kx + 35, ky - 42)], fill=(148, 163, 184), width=2)
            # Red Umbrella over Kitten
            ux, uy = kx + 35, ky - 100
            draw.chord([ux - 55, uy - 40, ux + 55, uy + 40], start=180, end=0, fill=(239, 68, 68))
            draw.line([(ux, uy), (ux, ky)], fill=(71, 85, 105), width=3)
            draw.arc([ux - 10, ky - 10, ux, ky], start=0, end=180, fill=(71, 85, 105), width=3)

        elif is_duck:
            # Round Yellow Duckling (Buli)
            dx, dy = cx, cy + 15
            body_r = int(min(width, height) * 0.11)
            draw.ellipse([dx - body_r, dy - body_r + 20, dx + body_r, dy + body_r + 55], fill=(250, 204, 21))
            head_r = int(body_r * 0.85)
            head_y = dy - int(body_r * 0.45)
            draw.ellipse([dx - head_r, head_y - head_r, dx + head_r, head_y + head_r], fill=(253, 224, 71))
            eye_off = int(head_r * 0.35)
            draw.ellipse([dx - eye_off - 7, head_y - 12, dx - eye_off + 7, head_y + 12], fill=(15, 23, 42))
            draw.ellipse([dx + eye_off - 7, head_y - 12, dx + eye_off + 7, head_y + 12], fill=(15, 23, 42))
            draw.ellipse([dx - eye_off - 4, head_y - 8, dx - eye_off + 2, head_y - 2], fill=(255, 255, 255))
            draw.ellipse([dx + eye_off + 1, head_y - 8, dx + eye_off + 7, head_y - 2], fill=(255, 255, 255))
            beak_w = int(head_r * 0.32)
            draw.polygon([(dx - beak_w, head_y + 8), (dx + beak_w, head_y + 8), (dx, head_y + 24)], fill=(249, 115, 22))
            # Red Scarf
            draw.rectangle([dx - head_r + 5, head_y + head_r - 8, dx + head_r - 5, head_y + head_r + 14], fill=(239, 68, 68))

        elif is_lamb:
            # Fluffy White Lamb with Curly Cloud Wool
            lx, ly = cx, cy + 15
            # Cloud wool body
            for ox, oy in [(-30, 0), (0, -15), (30, 0), (-20, 25), (20, 25), (0, 15)]:
                draw.ellipse([lx + ox - 28, ly + oy - 28, lx + ox + 28, ly + oy + 28], fill=(255, 255, 255))
            # Head
            draw.ellipse([lx - 32, ly - 80, lx + 32, ly - 20], fill=(254, 242, 242))
            # Pink Inner Ears
            draw.ellipse([lx - 48, ly - 65, lx - 25, ly - 45], fill=(244, 114, 182))
            draw.ellipse([lx + 25, ly - 65, lx + 48, ly - 45], fill=(244, 114, 182))
            # Eyes & Smile
            draw.ellipse([lx - 18, ly - 58, lx - 6, ly - 44], fill=(15, 23, 42))
            draw.ellipse([lx + 6, ly - 58, lx + 18, ly - 44], fill=(15, 23, 42))
            draw.ellipse([lx - 15, ly - 56, lx - 9, ly - 50], fill=(255, 255, 255))
            draw.ellipse([lx + 9, ly - 56, lx + 15, ly - 50], fill=(255, 255, 255))
            draw.arc([lx - 10, ly - 38, lx + 10, ly - 26], start=0, end=180, fill=(244, 63, 94), width=2)

        elif is_pony:
            # Friendly Brown Baby Foal
            hx = cx
            hy = cy - 20
            draw.ellipse([hx - 55, hy - 35, hx + 55, hy + 30], fill=(180, 83, 9))
            draw.polygon([(hx + 25, hy - 15), (hx + 65, hy - 80), (hx + 90, hy - 65), (hx + 45, hy + 10)], fill=(180, 83, 9))
            draw.ellipse([hx + 60, hy - 95, hx + 98, hy - 60], fill=(180, 83, 9))
            draw.polygon([(hx + 65, hy - 95), (hx + 70, hy - 110), (hx + 77, hy - 95)], fill=(146, 64, 14))
            draw.ellipse([hx + 75, hy - 85, hx + 81, hy - 79], fill=(15, 23, 42))
            draw.ellipse([hx + 85, hy - 75, hx + 102, hy - 58], fill=(251, 191, 36))
            for lx in [hx - 40, hx - 20, hx + 20, hx + 40]:
                draw.rectangle([lx, hy + 20, lx + 12, hy + 75], fill=(180, 83, 9))
                draw.rectangle([lx, hy + 70, lx + 12, hy + 80], fill=(30, 41, 59))

        elif is_rainbow:
            # Group Celebration: Puppy, Kitten, and Duckling dancing together!
            p_x = int(width * 0.38)
            draw.ellipse([p_x - 30, cy - 20, p_x + 30, cy + 35], fill=(250, 204, 21))
            draw.ellipse([p_x - 25, cy - 65, p_x + 25, cy - 15], fill=(217, 119, 6))
            draw.ellipse([p_x - 38, cy - 65, p_x - 20, cy - 25], fill=(180, 83, 9))
            draw.ellipse([p_x + 20, cy - 65, p_x + 38, cy - 25], fill=(180, 83, 9))

            k_x = int(width * 0.52)
            draw.ellipse([k_x - 28, cy - 20, k_x + 28, cy + 35], fill=(255, 255, 255))
            draw.ellipse([k_x - 25, cy - 65, k_x + 25, cy - 15], fill=(255, 255, 255))
            draw.polygon([(k_x - 22, cy - 58), (k_x - 14, cy - 80), (k_x - 4, cy - 62)], fill=(244, 114, 182))
            draw.polygon([(k_x + 4, cy - 62), (k_x + 14, cy - 80), (k_x + 22, cy - 58)], fill=(244, 114, 182))

            d_x = int(width * 0.65)
            draw.ellipse([d_x - 25, cy - 15, d_x + 25, cy + 30], fill=(250, 204, 21))
            draw.ellipse([d_x - 20, cy - 55, d_x + 20, cy - 10], fill=(253, 224, 71))
            draw.polygon([(d_x - 8, cy - 30), (d_x + 8, cy - 30), (d_x, cy - 18)], fill=(249, 115, 22))

        img.save(output_path, "JPEG", quality=95)
