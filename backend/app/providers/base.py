from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.models.timeline import WordTimestamp


class TTSResult(BaseModel):
    audio_path: str
    duration_seconds: float
    word_timestamps: List[WordTimestamp] = Field(default_factory=list)
    provider_name: str
    cost_usd: float = 0.0


class ScriptScene(BaseModel):
    scene_number: int
    narration: str
    estimated_duration: float
    visual_intent: str
    visual_source_preference: str = "user_or_stock"  # "user_image", "stock", "ai_image", "text_card"
    camera_motion: str = "slow_zoom_in"
    transition: str = "dissolve"
    sfx_hint: Optional[str] = None
    caption_emphasis: List[str] = Field(default_factory=list)


class ScriptResult(BaseModel):
    title: str
    hook: str
    body_summary: str
    call_to_action: str
    scenes: List[ScriptScene]
    language: str
    target_duration: float
    estimated_word_count: int
    provider_name: str
    cost_usd: float = 0.0


class ASRResult(BaseModel):
    transcript_text: str
    language: str
    duration_seconds: float
    words: List[WordTimestamp]
    provider_name: str
    cost_usd: float = 0.0


class TTSProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_path: str = "output.mp3",
        language: str = "bn",
        **kwargs
    ) -> TTSResult:
        """Synthesize text to speech and extract duration and word-level timestamps."""
        pass


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def generate_script(
        self,
        topic_or_content: str,
        language: str = "bn",
        target_duration: float = 60.0,
        tone: str = "educational"
    ) -> ScriptResult:
        """Analyze content and generate hooked script with scene breakdown."""
        pass


class ASRProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> ASRResult:
        """Transcribe audio with word-level timestamps."""
        pass
