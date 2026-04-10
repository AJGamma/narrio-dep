"""Job management system."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from ..models.job import Job, JobCreate, JobStatus, JobStage

logger = logging.getLogger(__name__)


class JobManager:
    """Manages job lifecycle, persistence, and status updates."""

    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize job manager.

        Args:
            storage_dir: Directory for job persistence. Defaults to .narrio/jobs
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.cwd() / ".narrio" / "jobs"

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory job store
        self._jobs: dict[str, Job] = {}

        # WebSocket callback for broadcasting updates
        self._broadcast_callback: Optional[Callable[[str, dict], Coroutine]] = None

        # Load existing jobs from storage
        self._load_jobs()

    def _load_jobs(self) -> None:
        """Load jobs from persistent storage."""
        for job_file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(job_file.read_text())
                job = Job(**data)
                self._jobs[job.id] = job
                logger.info(f"Loaded job {job.id} from storage")
            except Exception as e:
                logger.error(f"Failed to load job from {job_file}: {e}")

    def _save_job(self, job: Job) -> None:
        """Persist job to storage."""
        job_file = self.storage_dir / f"{job.id}.json"
        job_file.write_text(json.dumps(job.model_dump(mode="json"), indent=2))

    def set_broadcast_callback(
        self, callback: Callable[[str, dict], Coroutine]
    ) -> None:
        """Set callback for broadcasting job updates via WebSocket."""
        self._broadcast_callback = callback

    async def _broadcast_update(self, job_id: str, update: dict) -> None:
        """Broadcast job update to WebSocket clients."""
        if self._broadcast_callback:
            try:
                await self._broadcast_callback(job_id, update)
            except Exception as e:
                logger.error(f"Broadcast failed for job {job_id}: {e}")

    def create_job(self, job_create: JobCreate) -> Job:
        """Create a new job.

        Args:
            job_create: Job creation request

        Returns:
            Created job
        """
        job = Job(
            id=str(uuid.uuid4()),
            input_type=job_create.input_type,
            input_value=job_create.input_value,
            selected_style=job_create.selected_style,
        )
        self._jobs[job.id] = job
        self._save_job(job)
        logger.info(f"Created job {job.id}")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        return self._jobs.get(job_id)

    def get_all_jobs(
        self,
        status: Optional[JobStatus] = None,
        date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """Get all jobs with optional filtering.

        Args:
            status: Filter by status
            date: Filter by date (YYYY-MM-DD)
            limit: Maximum results
            offset: Result offset

        Returns:
            Tuple of (jobs list, total count)
        """
        jobs = list(self._jobs.values())

        # Filter by status
        if status:
            jobs = [j for j in jobs if j.status == status]

        # Filter by date
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
                jobs = [
                    j
                    for j in jobs
                    if j.created_at.date() == target_date
                ]
            except ValueError:
                pass

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        total = len(jobs)
        paginated = jobs[offset : offset + limit]

        return paginated, total

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage: Optional[JobStage] = None,
        progress: Optional[int] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and broadcast to clients.

        Args:
            job_id: Job identifier
            status: New status
            stage: Current pipeline stage
            progress: Progress percentage
            result: Job result data
            error: Error message if failed

        Returns:
            Updated job if found, None otherwise
        """
        job = self._jobs.get(job_id)
        if not job:
            return None

        job.update_status(status=status, stage=stage, progress=progress)

        if result is not None:
            job.result = result
        if error is not None:
            job.error = error

        self._save_job(job)

        # Broadcast update
        update = {
            "job_id": job_id,
            "status": job.status.value,
            "stage": job.stage.value if job.stage else None,
            "progress": job.progress,
            "updated_at": job.updated_at.isoformat(),
        }

        # Include result in broadcast for completed jobs
        if status == JobStatus.COMPLETED and result is not None:
            update["result"] = result
            logger.info(f"Job {job_id} completed with result")

        # Include error in broadcast for failed jobs
        if status == JobStatus.FAILED and error is not None:
            update["error"] = error

        logger.info(f"Updated job {job_id}: {status.value} (stage: {job.stage.value if job.stage else 'None'}, progress: {progress}%)")
        logger.debug(f"Broadcasting update: {update}")

        # Broadcast the update
        asyncio.create_task(self._broadcast_update(job_id, update))

        return job

    async def cancel_job(self, job_id: str) -> tuple[Optional[Job], Optional[str]]:
        """Cancel a job.

        Args:
            job_id: Job identifier

        Returns:
            Tuple of (job, error message)
        """
        job = self._jobs.get(job_id)
        if not job:
            return None, "Job not found"

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED):
            return job, f"Job already in {job.status.value} state"

        job.status = JobStatus.CANCELED
        job.completed_at = datetime.utcnow()
        self._save_job(job)

        # Broadcast update
        update = {
            "job_id": job_id,
            "status": JobStatus.CANCELED.value,
            "stage": None,
            "progress": job.progress,
            "updated_at": job.updated_at.isoformat(),
        }
        asyncio.create_task(self._broadcast_update(job_id, update))

        logger.info(f"Canceled job {job_id}")
        return job, None

    async def retry_job(self, job_id: str) -> tuple[Optional[Job], Optional[str]]:
        """Retry a failed or completed job.

        Args:
            job_id: Job identifier

        Returns:
            Tuple of (new job, error message)
        """
        old_job = self._jobs.get(job_id)
        if not old_job:
            return None, "Job not found"

        # Create new job with same parameters
        job_create = JobCreate(
            input_type=old_job.input_type,
            input_value=old_job.input_value,
            selected_style=old_job.selected_style,
        )
        new_job = self.create_job(job_create)

        # Copy metadata if needed
        new_job.metadata["retried_from"] = job_id

        logger.info(f"Retried job {job_id} as {new_job.id}")
        return new_job, None

    def get_job_result(self, job_id: str) -> Optional[dict]:
        """Get job result data.

        Args:
            job_id: Job identifier

        Returns:
            Result data if available
        """
        job = self._jobs.get(job_id)
        if not job:
            return None
        return job.result

    def cleanup_old_jobs(self, retention_days: int = 7) -> int:
        """Remove old completed jobs.

        Args:
            retention_days: Days to retain jobs

        Returns:
            Number of jobs removed
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        removed = 0

        for job_id, job in list(self._jobs.items()):
            if job.status in (JobStatus.COMPLETED, JobStatus.CANCELED, JobStatus.FAILED):
                if job.completed_at and job.completed_at < cutoff:
                    del self._jobs[job_id]
                    job_file = self.storage_dir / f"{job_id}.json"
                    if job_file.exists():
                        job_file.unlink()
                    removed += 1
                    logger.info(f"Removed old job {job_id}")

        return removed


# Global job manager instance
job_manager = JobManager()
