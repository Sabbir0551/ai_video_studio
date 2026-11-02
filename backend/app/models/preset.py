from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class CaptionPreset(BaseModel):
    font_name: str = "Noto Sans Bengali"
    font_size: int = 54
    primary_color: str = "&H00FFFFFF"      # White (ASS format)
    outline_color: str = "&H00000000"      # Black
    back_color: str = "&H80000000"         # Semi-transparent shadow
    bold: bool = True
    outline_width: int = 3
    shadow_depth: int = 1
    alignment: int = 2                     # Bottom center
    margin_v: int = 50                     # Vertical safe margin in pixels
    highlight_active_word: bool = True     # TikTok karaoke style


class AudioPreset(BaseModel):
    target_lufs: float = -14.0
    true_peak: float = -1.0
    music_volume: float = 0.15
    music_ducking_reduction_db: float = -12.0
    music_ducking_threshold_db: float = -24.0


class VisualPreset(BaseModel):
    ken_burns_enabled: bool = True
    default_transition: str = "dissolve"
    transition_duration: float = 0.5
    color_grading_preset: Optional[str] = None


class Preset(BaseModel):
    name: str
    description: str
    aspect_ratio: str = "16:9"
    fps: int = 30
    visual: VisualPreset = Field(default_factory=VisualPreset)
    audio: AudioPreset = Field(default_factory=AudioPreset)
    caption: CaptionPreset = Field(default_factory=CaptionPreset)
