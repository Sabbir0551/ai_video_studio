from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class AspectRatio(str, Enum):
    HORIZONTAL_16_9 = "16:9"
    VERTICAL_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    PORTRAIT_4_5 = "4:5"


class TrackType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    VOICE = "voice"
    MUSIC = "music"
    SFX = "sfx"
    CAPTIONS = "captions"
    OVERLAYS = "overlays"


class TransitionType(str, Enum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE_BLACK = "fade_black"
    FADE_WHITE = "fade_white"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    SLIDE_UP = "slide_up"
    ZOOM_IN = "zoom_in"


class Transition(BaseModel):
    type: TransitionType = TransitionType.DISSOLVE
    duration: float = Field(default=0.5, ge=0.0, le=5.0)


class KenBurnsEffect(BaseModel):
    start_scale: float = Field(default=1.0, ge=0.5, le=3.0)
    end_scale: float = Field(default=1.1, ge=0.5, le=3.0)
    pan_x: float = Field(default=0.0, ge=-1.0, le=1.0)
    pan_y: float = Field(default=0.0, ge=-1.0, le=1.0)


class Transform(BaseModel):
    crop_x: Optional[float] = None
    crop_y: Optional[float] = None
    crop_w: Optional[float] = None
    crop_h: Optional[float] = None
    scale: float = Field(default=1.0, gt=0.0)
    position_x: float = 0.0
    position_y: float = 0.0
    ken_burns: Optional[KenBurnsEffect] = None


class SidechainDucking(BaseModel):
    source_track_id: str
    threshold_db: float = Field(default=-24.0, le=0.0)
    reduction_db: float = Field(default=-12.0, le=0.0)
    attack_ms: float = Field(default=20.0, ge=1.0)
    release_ms: float = Field(default=300.0, ge=10.0)


class WordTimestamp(BaseModel):
    word: str
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)

    @field_validator("end")
    @classmethod
    def end_must_be_after_start(cls, v: float, info: Any) -> float:
        if "start" in info.data and v < info.data["start"]:
            raise ValueError(f"Word end time {v} cannot be earlier than start {info.data['start']}")
        return v


class CaptionItem(BaseModel):
    id: str
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)
    text: str
    words: Optional[List[WordTimestamp]] = None
    style: str = "default"
    position_y: Optional[float] = None  # percentage from top or pixel safe margin


class Clip(BaseModel):
    id: str
    source_path: str
    source_in: float = Field(default=0.0, ge=0.0)
    source_out: float = Field(ge=0.0)
    timeline_start: float = Field(ge=0.0)
    timeline_end: float = Field(ge=0.0)
    speed: float = Field(default=1.0, gt=0.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    transform: Optional[Transform] = None
    transition_in: Optional[Transition] = None
    transition_out: Optional[Transition] = None
    sidechain_ducking: Optional[SidechainDucking] = None

    @field_validator("timeline_end")
    @classmethod
    def timeline_end_must_be_after_start(cls, v: float, info: Any) -> float:
        if "timeline_start" in info.data and v <= info.data["timeline_start"]:
            raise ValueError(f"Clip timeline_end ({v}) must be greater than timeline_start ({info.data['timeline_start']})")
        return v


class Track(BaseModel):
    id: str
    name: str
    track_type: TrackType
    z_index: int = 0
    muted: bool = False
    clips: List[Clip] = Field(default_factory=list)


class CanvasConfig(BaseModel):
    width: int = Field(default=1920, ge=320)
    height: int = Field(default=1080, ge=240)
    aspect_ratio: AspectRatio = AspectRatio.HORIZONTAL_16_9
    fps: int = Field(default=30, ge=12, le=120)


class AudioConfig(BaseModel):
    sample_rate: int = Field(default=48000, ge=16000)
    channels: int = Field(default=2, ge=1, le=6)
    target_lufs: float = Field(default=-14.0, ge=-30.0, le=-6.0)
    true_peak: float = Field(default=-1.0, le=0.0)


class Timeline(BaseModel):
    version: str = "1.0"
    project_id: str
    canvas: CanvasConfig = Field(default_factory=CanvasConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    tracks: List[Track] = Field(default_factory=list)
    captions: List[CaptionItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def total_duration(self) -> float:
        """Calculate total timeline duration across all tracks and captions."""
        max_duration = 0.0
        for track in self.tracks:
            for clip in track.clips:
                if clip.timeline_end > max_duration:
                    max_duration = clip.timeline_end
        for cap in self.captions:
            if cap.end > max_duration:
                max_duration = cap.end
        return max_duration
