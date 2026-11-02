from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CHECKPOINT = "checkpoint"  # Human-in-the-loop review point
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class StageRecord(BaseModel):
    name: str
    description: str
    status: StageStatus = StageStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    cache_hit: bool = False


class Job(BaseModel):
    id: str
    project_id: str
    job_type: str  # "create_video", "analyze_video", "auto_edit_video", "render_timeline"
    status: JobStatus = JobStatus.PENDING
    progress_percent: float = 0.0
    current_stage: Optional[str] = None
    stages: List[StageRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = 0.0
    output_files: List[str] = Field(default_factory=list)
