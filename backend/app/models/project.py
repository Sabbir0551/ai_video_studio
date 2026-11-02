from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FONT = "font"
    DOCUMENT = "document"


class Asset(BaseModel):
    id: str
    project_id: str
    asset_type: AssetType
    file_path: str
    original_filename: str
    mime_type: Optional[str] = None
    file_size_bytes: int = 0
    license_type: str = "proprietary_user"  # proprietary_user, creative_commons, pexels, etc.
    attribution: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Project(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    language: str = "bn"  # "bn" or "en"
    aspect_ratio: str = "16:9"
    preset_name: str = "default_16x9"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
