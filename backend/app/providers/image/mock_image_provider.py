import os
from pathlib import Path
from PIL import Image, ImageDraw
from backend.app.providers.image.base import ImageGenProvider, ImageGenResult


class MockImageGenProvider(ImageGenProvider):
    """High-quality procedural image generator for offline testing and zero-cost fallback."""

    @property
    def name(self) -> str:
        return "procedural-mock"

    async def generate_or_source_image(
        self,
        query_or_prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        **kwargs
    ) -> ImageGenResult:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine color theme based on query
        q_lower = query_or_prompt.lower()
        if any(w in q_lower for w in ["ai", "tech", "computer", "future"]):
            base_color = (15, 23, 42)    # Dark slate
            accent_color = (56, 189, 248) # Sky blue
        elif any(w in q_lower for w in ["nature", "health", "green"]):
            base_color = (6, 38, 28)     # Forest dark
            accent_color = (52, 211, 153) # Mint green
        else:
            base_color = (24, 15, 36)    # Deep purple
            accent_color = (251, 146, 60) # Amber orange

        img = Image.new("RGB", (width, height), base_color)
        draw = ImageDraw.Draw(img)

        # Smooth vertical color gradient
        for y in range(height):
            ratio = y / height
            r = int(base_color[0] + ratio * 30)
            g = int(base_color[1] + ratio * 40)
            b = int(base_color[2] + ratio * 60)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Ambient decorative geometric shapes
        cx, cy = int(width * 0.7), int(height * 0.35)
        radius = int(min(width, height) * 0.3)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=accent_color, width=4)

        # Subtle secondary rectangle
        rx, ry = int(width * 0.15), int(height * 0.6)
        draw.rectangle([rx, ry, rx + 240, ry + 160], outline=(accent_color[0], accent_color[1], accent_color[2]), width=2)

        img.save(output_path, "PNG")

        return ImageGenResult(
            image_path=output_path,
            width=width,
            height=height,
            provider_name=self.name,
            license_type="CC0 Procedural",
            attribution="Generated procedurally by AI Video Studio",
            cost_usd=0.0
        )
