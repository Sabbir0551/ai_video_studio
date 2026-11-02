from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class EditOperationType(str, Enum):
    CUT_SILENCE = "cut_silence"
    CUT_FILLER = "cut_filler"
    PUNCH_IN_ZOOM = "punch_in_zoom"
    INSERT_BROLL = "insert_broll"
    AUTO_REFRAME = "auto_reframe"
    AUDIO_DENOISE = "audio_denoise"
    ADD_LOWER_THIRD = "add_lower_third"


class EditDecision(BaseModel):
    id: str
    operation: EditOperationType
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    reason: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    accepted: bool = True  # Human-in-the-loop review flag
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class ShotBoundary(BaseModel):
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    keyframe_path: Optional[str] = None


class WordDetail(BaseModel):
    word: str
    start: float
    end: float
    confidence: float = 1.0
    is_filler: bool = False


class AudioAnalysis(BaseModel):
    integrated_lufs: float
    true_peak_db: float
    silence_segments: List[List[float]] = Field(default_factory=list)  # [[start, end], ...]
    has_clipping: bool = False
    noise_floor_db: float = -60.0


class AnalysisReport(BaseModel):
    video_path: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    language: str
    transcript_text: str
    words: List[WordDetail] = Field(default_factory=list)
    shots: List[ShotBoundary] = Field(default_factory=list)
    audio: AudioAnalysis
    summary: str = ""
    suggested_edits: List[EditDecision] = Field(default_factory=list)
