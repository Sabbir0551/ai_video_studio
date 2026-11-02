import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.project import Project, Asset
from backend.app.models.job import Job, JobStatus


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.data_dir / "studio.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    language TEXT NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    preset_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_percent REAL NOT NULL,
                    current_stage TEXT,
                    stages_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    params_json TEXT,
                    cost_usd REAL NOT NULL,
                    output_files_json TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    mime_type TEXT,
                    file_size_bytes INTEGER NOT NULL,
                    license_type TEXT NOT NULL,
                    attribution TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
            """)
            conn.commit()

    def save_project(self, project: Project) -> None:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO projects (id, title, description, language, aspect_ratio, preset_name, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    language=excluded.language,
                    aspect_ratio=excluded.aspect_ratio,
                    preset_name=excluded.preset_name,
                    updated_at=excluded.updated_at,
                    metadata_json=excluded.metadata_json
            """, (
                project.id, project.title, project.description, project.language,
                project.aspect_ratio, project.preset_name,
                project.created_at.isoformat(), project.updated_at.isoformat(),
                json.dumps(project.metadata)
            ))
            conn.commit()

    def get_project(self, project_id: str) -> Optional[Project]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return Project(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                language=row["language"],
                aspect_ratio=row["aspect_ratio"],
                preset_name=row["preset_name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata_json"] or "{}")
            )

    def save_job(self, job: Job) -> None:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (id, project_id, job_type, status, progress_percent, current_stage, stages_json,
                                  created_at, started_at, completed_at, error_message, params_json, cost_usd, output_files_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    progress_percent=excluded.progress_percent,
                    current_stage=excluded.current_stage,
                    stages_json=excluded.stages_json,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    error_message=excluded.error_message,
                    cost_usd=excluded.cost_usd,
                    output_files_json=excluded.output_files_json
            """, (
                job.id, job.project_id, job.job_type, job.status.value,
                job.progress_percent, job.current_stage,
                json.dumps([s.model_dump(mode="json") for s in job.stages]),
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.error_message,
                json.dumps(job.params),
                job.cost_usd,
                json.dumps(job.output_files)
            ))
            conn.commit()

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return Job(
                id=row["id"],
                project_id=row["project_id"],
                job_type=row["job_type"],
                status=JobStatus(row["status"]),
                progress_percent=row["progress_percent"],
                current_stage=row["current_stage"],
                stages=json.loads(row["stages_json"] or "[]"),
                created_at=row["created_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                error_message=row["error_message"],
                params=json.loads(row["params_json"] or "{}"),
                cost_usd=row["cost_usd"],
                output_files=json.loads(row["output_files_json"] or "[]")
            )


db = Database()
