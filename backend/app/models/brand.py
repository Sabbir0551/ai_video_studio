from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class WatermarkPosition(str, Enum):
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"


class BrandKit(BaseModel):
    name: str = "Default Brand"
    logo_path: Optional[str] = "assets/brand/logo_watermark.png"
    watermark_position: WatermarkPosition = WatermarkPosition.TOP_RIGHT
    watermark_opacity: float = Field(default=0.85, ge=0.1, le=1.0)
    watermark_scale: float = Field(default=0.15, ge=0.05, le=0.5)
    margin_pixels: int = Field(default=30, ge=10, le=120)
    intro_clip_path: Optional[str] = None
    outro_clip_path: Optional[str] = None
    primary_color: str = "#0EA5E9"
    secondary_color: str = "#38BDF8"
    font_family: str = "Noto Sans Bengali"
