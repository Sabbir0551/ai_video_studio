import time
from backend.app.core.queue import JobQueue
from backend.app.core.db import db
from backend.app.models.job import Job, JobStatus, StageRecord, StageStatus


def test_job_queue_execution():
    test_queue = JobQueue(num_workers=1)
    executed = []

    def sample_handler(job: Job, q: JobQueue):
        q.update_stage(job.id, "stage_1", StageStatus.RUNNING)
        executed.append(job.id)
        q.update_stage(job.id, "stage_1", StageStatus.COMPLETED)

    test_queue.register_handler("test_job_type", sample_handler)
    test_queue.start_workers()

    job = Job(
        id="job_unit_01",
        project_id="proj_01",
        job_type="test_job_type",
        stages=[StageRecord(name="stage_1", description="Initial testing stage")]
    )

    test_queue.enqueue(job)

    # Wait for completion
    timeout = 5.0
    start = time.time()
    while time.time() - start < timeout:
        saved_job = db.get_job("job_unit_01")
        if saved_job and saved_job.status == JobStatus.COMPLETED:
            break
        time.sleep(0.1)

    saved_job = db.get_job("job_unit_01")
    assert saved_job is not None
    assert saved_job.status == JobStatus.COMPLETED
    assert "job_unit_01" in executed
    assert saved_job.progress_percent == 100.0
    test_queue.stop_workers()
