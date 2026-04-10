"""Job management API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..models.job import JobStatus, JobListResponse, JobResponse
from ..services.job_manager import job_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    date: Optional[str] = Query(default=None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(default=20, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
):
    """List jobs with pagination and filtering."""
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status.upper())
        except ValueError:
            return JobListResponse(
                data=[],
                total=0,
                error={"code": "INVALID_STATUS", "message": f"Invalid status: {status}"},
            )

    jobs, total = job_manager.get_all_jobs(
        status=status_filter,
        date=date,
        limit=limit,
        offset=offset,
    )

    return JobListResponse(data=jobs, total=total)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status and progress."""
    job = job_manager.get_job(job_id)

    if not job:
        return JobResponse(
            data=None,
            error={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        )

    return JobResponse(data=job, error=None)


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Get job result data."""
    job = job_manager.get_job(job_id)

    if not job:
        return {
            "data": None,
            "error": {"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        }

    if job.status != JobStatus.COMPLETED:
        return {
            "data": None,
            "error": {
                "code": "NOT_READY",
                "message": f"Job status is {job.status.value}, not COMPLETED",
            },
        }

    return {"data": job.result, "error": None}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    job, error = await job_manager.cancel_job(job_id)

    if error:
        if "not found" in error.lower():
            return {
                "data": None,
                "error": {"code": "NOT_FOUND", "message": error},
            }
        else:
            return {
                "data": None,
                "error": {"code": "BAD_REQUEST", "message": error},
            }

    return {"data": job, "error": None}


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """Retry a failed or completed job."""
    new_job, error = await job_manager.retry_job(job_id)

    if error:
        return {
            "data": None,
            "error": {"code": "BAD_REQUEST", "message": error},
        }

    return {"data": new_job, "error": None}


@router.get("/jobs/{job_id}/images/{filename}")
async def get_job_image(job_id: str, filename: str):
    """Get a generated image for a job."""
    # Get job to find run_dir
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Get run_dir from job result metadata
    run_dir = None
    if job.result and "metadata" in job.result:
        run_dir = job.result["metadata"].get("run_dir")

    if not run_dir:
        logger.error(f"No run_dir found in job {job_id} result")
        raise HTTPException(status_code=404, detail="Image directory not found for this job")

    # Construct image path
    image_path = Path(run_dir) / "render" / filename

    # Security check: ensure the path is within run_dir
    try:
        image_path = image_path.resolve()
        run_dir_path = Path(run_dir).resolve()
        if not str(image_path).startswith(str(run_dir_path)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        logger.error(f"Path resolution error for job {job_id}, file {filename}: {e}")
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Check if file exists
    if not image_path.exists() or not image_path.is_file():
        logger.error(f"Image not found: {image_path}")
        raise HTTPException(status_code=404, detail=f"Image {filename} not found")

    logger.info(f"Serving image {filename} for job {job_id} from {image_path}")

    # Return the image file
    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=filename
    )
