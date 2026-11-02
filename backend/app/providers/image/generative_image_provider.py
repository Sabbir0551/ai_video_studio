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
    - Robust failover to dynamic scene-specific vector/procedural illustration if offline.
    """

    def __init__(self, default_seed: Optional[int] = None):
        self._default_seed = default_seed or 42891

    @property
    def name(self) -> str:
        return "generative-ai"

    def _extract_character_and_seed(self, prompt: str) -> int:
        """Derive a consistent integer seed from character name or prompt anchor."""
        char_match = re.search(r"character\s*:\s*([^,\.\n]+)", prompt, re.IGNORECASE)
        if char_match:
            char_name = char_match.group(1).strip().lower()
            return abs(hash(char_name)) % 999999
        return self._default_seed

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
        height: int = 1080
    ) -> ImageGenResult:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        seed = self._extract_character_and_seed(query_or_prompt)

        clean_prompt = re.sub(r'[\*\#\_\"\'\`]', '', query_or_prompt)
        clean_prompt = re.sub(r'\s+', ' ', clean_prompt).strip()
        if len(clean_prompt) > 280:
            clean_prompt = clean_prompt[:280]

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
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={req_w}&height={req_h}&seed={seed}"
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
                        logger.info(f"Generated AI character visual for: '{clean_prompt[:50]}...' -> {output_path}")
                    elif resp.status_code == 402:
                        logger.warning("Pollinations rate limit reached (1 image every 45s without key).")
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
        """Render a vibrant, multi-layered storybook illustration dynamically matching the actual scene prompt."""
        p_lower = prompt.lower()
        is_night = any(w in p_lower for w in ["night", "stars", "sleep", "moon"])
        is_sunset = any(w in p_lower for w in ["sunset", "dusk", "orange", "pink", "evening"])
        is_rain = any(w in p_lower for w in ["rain", "cloud", "storm", "gray", "grey"])
        is_farm = any(w in p_lower for w in ["farm", "barn", "horse", "cow", "stable", "hay"])
        is_duck = any(w in p_lower for w in ["duck", "duckling", "buli"])
        is_tuni = any(w in p_lower for w in ["tuni", "girl", "child", "toddler", "kid"]) and not is_duck

        img = Image.new("RGB", (width, height), (135, 206, 235))
        draw = ImageDraw.Draw(img)

        # 1. Sky Gradient
        if is_night:
            top_sky = (15, 23, 42)
            bottom_sky = (30, 41, 59)
        elif is_sunset:
            top_sky = (124, 45, 18)
            bottom_sky = (249, 115, 22)
        elif is_rain:
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

        # 2. Celestial Body (Sun/Moon/Clouds)
        sun_x = int(width * 0.8)
        sun_y = int(height * 0.22)
        sun_r = int(min(width, height) * 0.1)

        if is_night:
            # Moon & Stars
            draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(254, 240, 138))
            draw.ellipse([sun_x - sun_r + 20, sun_y - sun_r - 10, sun_x + sun_r + 20, sun_y + sun_r - 10], fill=(bottom_sky[0], bottom_sky[1], bottom_sky[2]))
            for i in range(30):
                sx = int((seed * 37 + i * 137) % (width * 0.9))
                sy = int((seed * 19 + i * 83) % (height * 0.5))
                draw.ellipse([sx, sy, sx + 4, sy + 4], fill=(255, 255, 255))
        elif is_rain:
            # Rain Clouds & Drops
            for cx in [int(width * 0.3), int(width * 0.6), int(width * 0.8)]:
                cy = int(height * 0.2)
                draw.ellipse([cx - 90, cy - 40, cx + 90, cy + 40], fill=(100, 116, 139))
                draw.ellipse([cx - 50, cy - 70, cx + 50, cy + 10], fill=(100, 116, 139))
            # Raindrops
            for i in range(40):
                rx = int((seed * 23 + i * 97) % width)
                ry = int((seed * 41 + i * 67) % (height * 0.7))
                draw.line([(rx, ry), (rx - 4, ry + 16)], fill=(186, 230, 253), width=2)
        else:
            # Warm Glowing Sun
            draw.ellipse([sun_x - sun_r - 15, sun_y - sun_r - 15, sun_x + sun_r + 15, sun_y + sun_r + 15], fill=(254, 215, 170))
            draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(251, 191, 36))

        # 3. Ground / Meadow
        ground_y = int(height * 0.65)
        hill_bg = (34, 197, 94) if not is_night else (20, 83, 45)
        draw.chord([-100, ground_y - 80, int(width * 0.7), height + 100], start=180, end=0, fill=hill_bg)
        hill_fg = (22, 163, 74) if not is_night else (22, 101, 52)
        draw.chord([int(width * 0.3), ground_y - 60, width + 200, height + 100], start=180, end=0, fill=hill_fg)
        draw.rectangle([0, ground_y + 40, width, height], fill=hill_fg)

        # 4. Contextual Objects Based on Scene Content
        if is_farm:
            # Red Farm Barn with White Roof and Crossbeams
            bx = int(width * 0.15)
            bw = int(width * 0.35)
            bh = int(height * 0.3)
            by = ground_y - bh + 50

            # Barn Body
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(185, 28, 28))
            # Barn Roof (Gambrel Roof shape)
            draw.polygon([
                (bx - 20, by),
                (bx + int(bw * 0.2), by - 60),
                (bx + int(bw * 0.5), by - 90),
                (bx + int(bw * 0.8), by - 60),
                (bx + bw + 20, by)
            ], fill=(220, 38, 38))
            # Barn Door with White Cross
            door_w = int(bw * 0.4)
            door_h = int(bh * 0.6)
            dx = bx + int(bw * 0.3)
            dy = by + bh - door_h
            draw.rectangle([dx, dy, dx + door_w, dy + door_h], fill=(254, 242, 242))
            draw.line([(dx, dy), (dx + door_w, dy + door_h)], fill=(185, 28, 28), width=3)
            draw.line([(dx + door_w, dy), (dx, dy + door_h)], fill=(185, 28, 28), width=3)

            # Friendly 3D-style Brown Horse
            hx = int(width * 0.65)
            hy = ground_y - 20
            # Horse Body
            draw.ellipse([hx - 60, hy - 40, hx + 60, hy + 30], fill=(180, 83, 9))
            # Horse Neck & Head
            draw.polygon([(hx + 30, hy - 20), (hx + 70, hy - 90), (hx + 95, hy - 75), (hx + 50, hy + 10)], fill=(180, 83, 9))
            draw.ellipse([hx + 65, hy - 105, hx + 105, hy - 70], fill=(180, 83, 9))
            # Ears
            draw.polygon([(hx + 70, hy - 105), (hx + 75, hy - 120), (hx + 82, hy - 105)], fill=(146, 64, 14))
            # Eye & Muzzle
            draw.ellipse([hx + 80, hy - 95, hx + 86, hy - 89], fill=(15, 23, 42))
            draw.ellipse([hx + 90, hy - 85, hx + 110, hy - 65], fill=(251, 191, 36))
            # Legs
            for lx in [hx - 45, hx - 25, hx + 25, hx + 45]:
                draw.rectangle([lx, hy + 20, lx + 12, hy + 80], fill=(180, 83, 9))
                draw.rectangle([lx, hy + 75, lx + 12, hy + 85], fill=(30, 41, 59)) # Hoof

        if is_tuni:
            # Cute Toddler Girl Character (Tuni)
            tx = int(width * 0.45 if is_farm else width * 0.5)
            ty = ground_y - 20
            # Dress
            draw.polygon([(tx - 15, ty - 20), (tx + 15, ty - 20), (tx + 35, ty + 40), (tx - 35, ty + 40)], fill=(244, 114, 182))
            # Head
            draw.ellipse([tx - 25, ty - 70, tx + 25, ty - 20], fill=(254, 215, 170))
            # Hair Pigtails
            draw.ellipse([tx - 28, ty - 75, tx + 28, ty - 45], fill=(120, 53, 15))
            draw.ellipse([tx - 38, ty - 60, tx - 22, ty - 40], fill=(120, 53, 15))
            draw.ellipse([tx + 22, ty - 60, tx + 38, ty - 40], fill=(120, 53, 15))
            # Eyes & Smile
            draw.ellipse([tx - 12, ty - 50, tx - 6, ty - 42], fill=(15, 23, 42))
            draw.ellipse([tx + 6, ty - 50, tx + 12, ty - 42], fill=(15, 23, 42))
            draw.arc([tx - 8, ty - 38, tx + 8, ty - 28], start=0, end=180, fill=(239, 68, 68), width=2)
            # Legs
            draw.rectangle([tx - 14, ty + 40, tx - 4, ty + 70], fill=(254, 215, 170))
            draw.rectangle([tx + 4, ty + 40, tx + 14, ty + 70], fill=(254, 215, 170))

        elif is_duck:
            # Duckling Character (Buli)
            char_x = int(width * 0.5)
            char_y = int(ground_y + 10)
            body_r = int(min(width, height) * 0.12)
            draw.ellipse([char_x - body_r, char_y - body_r + 20, char_x + body_r, char_y + body_r + 60], fill=(250, 204, 21))
            head_r = int(body_r * 0.85)
            head_y = char_y - int(body_r * 0.5)
            draw.ellipse([char_x - head_r, head_y - head_r, char_x + head_r, head_y + head_r], fill=(253, 224, 71))
            eye_offset = int(head_r * 0.35)
            eye_y = head_y - 10
            draw.ellipse([char_x - eye_offset - 8, eye_y - 12, char_x - eye_offset + 8, eye_y + 12], fill=(15, 23, 42))
            draw.ellipse([char_x + eye_offset - 8, eye_y - 12, char_x + eye_offset + 8, eye_y + 12], fill=(15, 23, 42))
            draw.ellipse([char_x - eye_offset - 4, eye_y - 8, char_x - eye_offset + 2, eye_y - 2], fill=(255, 255, 255))
            draw.ellipse([char_x + eye_offset + 1, eye_y - 8, char_x + eye_offset + 7, eye_y - 2], fill=(255, 255, 255))
            beak_w = int(head_r * 0.3)
            draw.polygon([(char_x - beak_w, head_y + 10), (char_x + beak_w, head_y + 10), (char_x, head_y + 25)], fill=(249, 115, 22))
            scarf_y = head_y + head_r - 10
            draw.rectangle([char_x - head_r + 5, scarf_y, char_x + head_r - 5, scarf_y + 20], fill=(239, 68, 68))

        img.save(output_path, "JPEG", quality=95)
