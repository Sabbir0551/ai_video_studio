import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.core.config import settings

client = TestClient(app)


def test_home_page():
    """Verify that the single-page application serves 200 OK and contains UI elements."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AI Video Studio" in response.text
    assert "ড্যাশবোর্ড" in response.text


def test_health_endpoint():
    """Verify system health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.app_name
    assert "encoder" in data
    assert "timestamp" in data


def test_get_presets_endpoint():
    """Verify presets endpoint lists registered presets."""
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    presets = response.json()
    assert isinstance(presets, list)
    assert len(presets) >= 4
    names = [p["name"] for p in presets]
    assert "clean_corporate" in names
    assert "short_hype" in names
    assert "documentary" in names
    assert "news_flash" in names


def test_list_renders_endpoint():
    """Verify rendered video gallery endpoint returns valid array."""
    response = client.get("/api/v1/renders")
    assert response.status_code == 200
    renders = response.json()
    assert isinstance(renders, list)


def test_create_video_preview_endpoint():
    """Test creating a quick preview video through the REST API."""
    payload = {
        "prompt": "এআই ভিডিও স্টুডিও এর ওয়েব ইন্টারফেস এখন পুরোপুরি কার্যকর।",
        "language": "bn",
        "aspect_ratio": "16:9",
        "preset_name": "clean_corporate",
        "preview": True,
        "watermark": True,
        "target_duration": 4.0
    }
    response = client.post("/api/v1/create-video", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "video_url" in data
    assert "qa" in data
    assert data["qa"]["passed"] is True
    assert data["qa"]["resolution"] == "960x540"


def test_analysis_and_edit_validation():
    """Verify validation errors when invalid video paths are provided."""
    res_analyze = client.post("/api/v1/analyze-video", json={"video_path": "invalid_missing_file.mp4"})
    assert res_analyze.status_code == 400
    assert "File not found" in res_analyze.json()["detail"]

    res_edit = client.post("/api/v1/edit-video", json={"video_path": "invalid_missing_file.mp4"})
    assert res_edit.status_code == 400
    assert "File not found" in res_edit.json()["detail"]
