"""Job data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class JobStage(str, Enum):
    """Pipeline stages."""

    CHUNKIFY = "chunkify"
    STYLIFY = "stylify"
    RENDER = "render"


class Job(BaseModel):
    """Job model representing a content generation request."""

    id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    stage: Optional[JobStage] = Field(default=None, description="Current pipeline stage")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")

    # Input parameters
    input_type: str = Field(..., description="Type of input: text, url, or audio")
    input_value: str = Field(..., description="Input content or URL")
    selected_style: Optional[str] = Field(default=None, description="Selected style for generation")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")

    # Results
    result: Optional[dict[str, Any]] = Field(default=None, description="Job result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def update_status(
        self, status: JobStatus, stage: Optional[JobStage] = None, progress: Optional[int] = None
    ) -> None:
        """Update job status and timestamps."""
        self.status = status
        self.updated_at = datetime.utcnow()

        if stage is not None:
            self.stage = stage
        if progress is not None:
            self.progress = max(0, min(100, progress))

        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED):
            self.completed_at = datetime.utcnow()


class JobCreate(BaseModel):
    """Request model for creating a job."""

    input_type: str = Field(..., description="Type of input: text, url, or audio")
    input_value: str = Field(..., description="Input content or URL")
    selected_style: Optional[str] = Field(default=None, description="Selected style for generation")


class JobResponse(BaseModel):
    """Response model for job operations."""

    data: Optional[Job] = Field(default=None, description="Job data")
    error: Optional[dict[str, Any]] = Field(default=None, description="Error details")


class JobListResponse(BaseModel):
    """Response model for listing jobs."""

    data: list[Job] = Field(default_factory=list, description="List of jobs")
    total: int = Field(default=0, description="Total job count")
    error: Optional[dict[str, Any]] = Field(default=None, description="Error details")
