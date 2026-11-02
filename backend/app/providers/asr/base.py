from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.models.timeline import WordTimestamp


class ASRResult(BaseModel):
    transcript_text: str
    language: str
    duration_seconds: float
    words: List[WordTimestamp] = Field(default_factory=list)
    confidence: float = 1.0
    provider_name: str
    cost_usd: float = 0.0


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
        """Transcribe audio file into text with word-level timestamps."""
        pass
