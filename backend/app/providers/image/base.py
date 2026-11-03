from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field


class ImageGenResult(BaseModel):
    image_path: str
    width: int
    height: int
    provider_name: str
    license_type: str = "open"
    attribution: Optional[str] = None
    cost_usd: float = 0.0


class ImageGenProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def generate_or_source_image(
        self,
        query_or_prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        **kwargs
    ) -> ImageGenResult:
        pass
