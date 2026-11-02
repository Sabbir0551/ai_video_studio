import time
import threading
import traceback
from datetime import datetime, timezone
from typing import Callable, Dict, Any, Optional
from queue import Queue, Empty
from backend.app.core.logging import logger
from backend.app.core.db import db
from backend.app.models.job import Job, JobStatus, StageRecord, StageStatus


class JobQueue:
    """Persistent, thread-safe asynchronous queue with stage management and retry logic."""
    def __init__(self, num_workers: int = 1):
        self._work_queue: Queue = Queue()
        self._registry: Dict[str, Callable] = {}
        self._num_workers = num_workers
        self._stop_event = threading.Event()
        self._workers = []
        self._lock = threading.Lock()
        self._active_jobs: Dict[str, Job] = {}

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """Register a handler function for a specific job_type."""
        with self._lock:
            self._registry[job_type] = handler
            logger.info(f"Registered job handler for '{job_type}'")

    def enqueue(self, job: Job) -> Job:
        """Save job to DB and add to processing queue."""
        job.status = JobStatus.PENDING
        db.save_job(job)
        self._work_queue.put(job.id)
        logger.info(f"Enqueued job {job.id} (type: {job.job_type})")
        return job

    def start_workers(self) -> None:
        """Start worker threads."""
        for i in range(self._num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"StudioWorker-{i+1}", daemon=True)
            t.start()
            self._workers.append(t)
        logger.info(f"Started {self._num_workers} background queue worker(s)")

    def stop_workers(self) -> None:
        """Signal workers to stop gracefully."""
        self._stop_event.set()

    def update_stage(self, job_id: str, stage_name: str, status: StageStatus, error: Optional[str] = None) -> None:
        """Update individual stage status for progress observability."""
        job = db.get_job(job_id)
        if not job:
            return

        now = datetime.now(timezone.utc)
        for stage in job.stages:
            if stage.name == stage_name:
                stage.status = status
                if status == StageStatus.RUNNING:
                    stage.started_at = now
                    job.current_stage = stage_name
                elif status in (StageStatus.COMPLETED, StageStatus.FAILED):
                    stage.completed_at = now
                    if stage.started_at:
                        stage.duration_seconds = (now - stage.started_at).total_seconds()
                    if error:
                        stage.error_message = error
                break

        # Calculate overall progress
        if job.stages:
            completed_stages = sum(1 for s in job.stages if s.status == StageStatus.COMPLETED)
            job.progress_percent = round((completed_stages / len(job.stages)) * 100, 1)

        db.save_job(job)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self._work_queue.get(timeout=1.0)
            except Empty:
                continue

            try:
                job = db.get_job(job_id)
                if not job:
                    continue

                if job.status == JobStatus.CANCELLED:
                    logger.info(f"Skipping cancelled job {job_id}")
                    continue

                handler = self._registry.get(job.job_type)
                if not handler:
                    job.status = JobStatus.FAILED
                    job.error_message = f"No handler registered for job type: {job.job_type}"
                    job.completed_at = datetime.now(timezone.utc)
                    db.save_job(job)
                    continue

                # Run Job
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                db.save_job(job)
                logger.info(f"Executing job {job.id} [{job.job_type}]")

                # Execute handler with retry/backoff if requested
                max_retries = 2
                attempt = 0
                success = False

                while attempt <= max_retries and not success:
                    try:
                        handler(job, self)
                        success = True
                    except Exception as ex:
                        attempt += 1
                        err_trace = traceback.format_exc()
                        logger.error(f"Error on job {job.id} (attempt {attempt}/{max_retries+1}): {ex}\n{err_trace}")
                        if attempt <= max_retries:
                            time.sleep(1.0 * attempt)  # backoff
                        else:
                            job.status = JobStatus.FAILED
                            job.error_message = str(ex)
                            job.completed_at = datetime.now(timezone.utc)
                            db.save_job(job)

                if success:
                    # Reload latest in case handler modified stages or outputs
                    current_job = db.get_job(job.id) or job
                    current_job.status = JobStatus.COMPLETED
                    current_job.progress_percent = 100.0
                    current_job.completed_at = datetime.now(timezone.utc)
                    db.save_job(current_job)
                    logger.info(f"Job {job.id} completed successfully")

            except Exception as e:
                logger.error(f"Unexpected queue worker error: {e}")
            finally:
                self._work_queue.task_done()


queue = JobQueue(num_workers=1)
