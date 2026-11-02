from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class VideoGenResult(BaseModel):
    video_path: str
    duration_seconds: float
    width: int
    height: int
    fps: int = 30
    provider_name: str
    cost_usd: float = 0.0
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class VideoGenProvider(ABC):
    """Abstract interface for AI Video Generation (Text-to-Video and Image-to-Video)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def animate_image_to_video(
        self,
        image_path: str,
        motion_prompt: str,
        duration: float = 5.0,
        output_path: str = "motion_clip.mp4",
        aspect_ratio: str = "16:9",
        width: int = 1920,
        height: int = 1080
    ) -> VideoGenResult:
        """Transform a 2D/3D still keyframe into a flowing, cinematic video clip with character motion."""
        pass
