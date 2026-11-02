import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.db import db
from backend.app.core.queue import queue
from backend.app.models.project import Project
from backend.app.models.job import Job
from backend.app.models.brand import BrandKit
from backend.app.presets.manager import preset_manager
from backend.app.pipelines.create_video.pipeline import create_video_pipeline
from backend.app.pipelines.edit_video.pipeline import auto_edit_pipeline
from backend.app.analysis.analyzer import multimodal_analyzer
from backend.app.media.ffmpeg_wrapper import ffmpeg

app = FastAPI(
    title="AI Video Studio API",
    version="0.5.0",
    description="Live REST API and Web Interface for AI Video Studio."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount Static Directories for Video Streaming & Assets
settings.init_directories()
renders_dir = settings.data_dir / "renders"
renders_dir.mkdir(parents=True, exist_ok=True)

static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/media/renders", StaticFiles(directory=str(renders_dir)), name="renders")
app.mount("/media/projects", StaticFiles(directory=str(settings.data_dir / "projects")), name="projects")


# -------------------------------------------------------------
# Data Transfer Objects (DTOs)
# -------------------------------------------------------------
class CreateVideoRequest(BaseModel):
    prompt: str
    language: str = "bn"
    aspect_ratio: str = "16:9"
    preset_name: str = "clean_corporate"
    watermark: bool = False
    preview: bool = False
    target_duration: float = 60.0
    openai_api_key: Optional[str] = None


class AnalyzeVideoRequest(BaseModel):
    video_path: str
    language: str = "bn"
    goal: str = "talking_head_polish"


class AutoEditRequest(BaseModel):
    video_path: str
    language: str = "bn"
    goal: str = "talking_head_polish"
    aggressiveness: str = "balanced"
    aspect_ratio: str = "16:9"
    punch_zooms: bool = True
    captions: bool = True
    music: bool = True


# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    settings.init_directories()
    queue.start_workers()


@app.get("/")
def serve_home():
    """Serve the Web UI single-page application."""
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Web UI not built.")
    return FileResponse(str(index_file))


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.studio_env,
        "encoder": ffmpeg.get_hardware_acceleration(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/presets")
def get_presets():
    return [p.model_dump() for p in preset_manager.list_presets()]


@app.get("/api/v1/renders")
def list_renders():
    """List all available rendered videos for the UI gallery."""
    results = []
    if renders_dir.exists():
        for f in renders_dir.glob("*.mp4"):
            try:
                probe = ffmpeg.probe_media(str(f))
                duration = float(probe.get("format", {}).get("duration", 0.0))
                streams = probe.get("streams", [])
                v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                w = v_stream.get("width", 0) if v_stream else 0
                h = v_stream.get("height", 0) if v_stream else 0

                lufs_data = ffmpeg.measure_lufs(str(f))
                results.append({
                    "filename": f.name,
                    "url": f"/media/renders/{f.name}",
                    "duration": round(duration, 1),
                    "resolution": f"{w}x{h}",
                    "lufs": round(lufs_data.get("integrated_lufs", -14.0), 1),
                    "size_bytes": f.stat().st_size
                })
            except Exception:
                results.append({
                    "filename": f.name,
                    "url": f"/media/renders/{f.name}",
                    "duration": 0,
                    "resolution": "unknown",
                    "lufs": -14.0,
                    "size_bytes": f.stat().st_size
                })
    results.sort(key=lambda x: x["filename"], reverse=True)
    return results


@app.post("/api/v1/create-video")
def create_video_endpoint(req: CreateVideoRequest):
    """Generate a broadcast video from text/script."""
    if req.openai_api_key and len(req.openai_api_key) > 5:
        os.environ["OPENAI_API_KEY"] = req.openai_api_key

    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    out_name = f"{project_id}_render.mp4"
    out_path = str(renders_dir / out_name)

    brand = BrandKit() if req.watermark else None

    res = create_video_pipeline.run(
        project_id=project_id,
        topic_or_content=req.prompt,
        language=req.language,
        aspect_ratio=req.aspect_ratio,
        preset_name=req.preset_name,
        target_duration=req.target_duration,
        output_path=out_path,
        brand_kit=brand,
        preview_mode=req.preview
    )

    return {
        "project_id": project_id,
        "video_url": f"/media/renders/{out_name}",
        "qa": res["qa"],
        "seo_metadata": res.get("seo_metadata"),
        "credits_path": res.get("credits_path")
    }


@app.post("/api/v1/analyze-video")
def analyze_video_endpoint(req: AnalyzeVideoRequest):
    """Analyze speech, silences, and shot cuts in a video."""
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=400, detail=f"File not found: {req.video_path}")

    project_id = f"analyze_{uuid.uuid4().hex[:8]}"
    report = multimodal_analyzer.analyze(
        video_path=req.video_path,
        project_id=project_id,
        language=req.language,
        goal=req.goal
    )
    return report.model_dump()


@app.post("/api/v1/edit-video")
def edit_video_endpoint(req: AutoEditRequest):
    """Auto-edit video removing silences & fillers with punch-in zooms."""
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=400, detail=f"File not found: {req.video_path}")

    project_id = f"edit_{uuid.uuid4().hex[:8]}"
    out_name = f"{project_id}_auto_edited.mp4"
    out_path = str(renders_dir / out_name)

    res = auto_edit_pipeline.edit(
        video_path=req.video_path,
        project_id=project_id,
        language=req.language,
        goal=req.goal,
        aggressiveness=req.aggressiveness,
        target_aspect_ratio=req.aspect_ratio,
        enable_punch_zooms=req.punch_zooms,
        add_captions=req.captions,
        add_music_bed=req.music,
        output_path=out_path
    )

    return {
        "project_id": project_id,
        "video_url": f"/media/renders/{out_name}",
        "comparison": res["comparison"],
        "qa": res["qa"]
    }
