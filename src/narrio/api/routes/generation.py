"""Content generation API endpoints."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File

from ...experiment import ExperimentRequest, execute_experiment
from ...paths import repo_paths
from ..models.job import JobCreate, JobStatus, JobStage, JobResponse
from ..services.job_manager import job_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_input(input_type: str, input_value: str) -> tuple[bool, Optional[str]]:
    """Validate generation input.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if input_type == "text":
        if len(input_value) < 100:
            return False, "Text input must be at least 100 characters"
        return True, None

    elif input_type == "url":
        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        if not url_pattern.match(input_value):
            return False, "Invalid URL format"
        return True, None

    elif input_type == "audio":
        # Audio validation happens via file upload
        return True, None

    else:
        return (
            False,
            f"Invalid input type: {input_type}. Must be 'text', 'url', or 'audio'",
        )


async def fetch_url_content(url: str) -> str:
    """Fetch content from a URL using the SSR scraper.

    Args:
        url: URL to fetch

    Returns:
        Markdown content from the URL

    Raises:
        HTTPException: If fetch fails
    """
    try:
        from ...ssr_service import get_scraper

        scraper = get_scraper()
        result = await scraper.scrape_url(url)
        return result["content"]
    except Exception as e:
        logger.error(f"Failed to scrape URL {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL content: {str(e)}")


async def run_generation_pipeline(
    job_id: str,
    input_type: str,
    input_value: str,
    selected_style: Optional[str],
    source_url: Optional[str] = None,
) -> None:
    """Run the content generation pipeline in background.

    This integrates with the core narrio experiment pipeline and
    reports progress via WebSocket callbacks.
    """
    try:
        logger.info(f"Starting generation pipeline for job {job_id}")

        # Update to RUNNING status immediately
        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.RUNNING,
            stage=None,
            progress=0,
        )

        loop = asyncio.get_running_loop()

        def progress_callback(stage_name: str, progress: int):
            """Progress callback called from worker thread."""
            try:
                stage = JobStage.CHUNKIFY
                if stage_name == "stylify":
                    stage = JobStage.STYLIFY
                elif stage_name == "render":
                    stage = JobStage.RENDER

                logger.debug(
                    f"Progress callback for job {job_id}: {stage_name} - {progress}%"
                )

                # Schedule the coroutine and wait for it to complete
                future = asyncio.run_coroutine_threadsafe(
                    job_manager.update_job_status(
                        job_id=job_id,
                        status=JobStatus.RUNNING,
                        stage=stage,
                        progress=progress,
                    ),
                    loop,
                )
                # Wait up to 2 seconds for the update to complete
                future.result(timeout=2.0)
                logger.debug(
                    f"Progress update completed for job {job_id}: {stage_name} - {progress}%"
                )
            except Exception as e:
                logger.error(
                    f"Failed to update progress for job {job_id}: {e}", exc_info=True
                )

        from ...config import load_config
        from ...experiment import ModelOverrides

        config = load_config()

        if input_type == "audio":
            # For audio, input_value is the temporary file path
            request = ExperimentRequest(
                content_type="podcast",
                markdown="",  # Will be set automatically by experiment pipeline from audio filename
                style=selected_style or "OpenAI弥散琉璃",
                start_stage="from-audio",
                audio_file=input_value,
                progress_callback=progress_callback,
                models=ModelOverrides(
                    chunk_model=config.text_api.model,
                    editorial_model=config.text_api.model,
                    image_model=config.image_api.model,
                ),
                text_api_key=config.text_api.api_key,
                image_api_key=config.image_api.api_key,
                text_base_url=config.text_api.base_url,
                image_base_url=config.image_api.base_url,
                image_api_format=config.image_api.format,
                asr_api_key=config.asr_api.api_key if config.asr_api else None,
                asr_app_key=config.asr_api.app_key if config.asr_api else None,
                asr_access_token=(
                    config.asr_api.access_token if config.asr_api else None
                ),
                asr_language=config.asr_api.language if config.asr_api else None,
            )
        else:
            # For text/url, write input_value to a file in content/sources/article/
            file_name = f"api_job_{job_id}.md"
            sources_dir = repo_paths().content_root / "sources" / "article"
            sources_dir.mkdir(parents=True, exist_ok=True)
            file_path = sources_dir / file_name
            file_path.write_text(input_value, encoding="utf-8")

            request = ExperimentRequest(
                content_type="article",
                markdown=file_name,
                style=selected_style or "OpenAI弥散琉璃",
                progress_callback=progress_callback,
                models=ModelOverrides(
                    chunk_model=config.text_api.model,
                    editorial_model=config.text_api.model,
                    image_model=config.image_api.model,
                ),
                text_api_key=config.text_api.api_key,
                image_api_key=config.image_api.api_key,
                text_base_url=config.text_api.base_url,
                image_base_url=config.image_api.base_url,
                image_api_format=config.image_api.format,
            )

        logger.info(
            f"Dispatching execute_experiment for job {job_id} with config: {request.content_type}, style: {request.style}"
        )

        result_dict = await asyncio.to_thread(execute_experiment, request)

        logger.info(
            f"Execute_experiment completed for job {job_id}, processing results..."
        )

        # Parse results
        from pathlib import Path

        run_dir = Path(result_dict["run_dir"])
        render_dir = run_dir / "render"
        images = []
        if render_dir.exists():
            for idx, img_path in enumerate(sorted(render_dir.glob("*.png"))):
                images.append(
                    {
                        "url": f"/api/jobs/{job_id}/images/{img_path.name}",
                        "page": idx + 1,
                    }
                )

        result = {
            "status": "completed",
            "output_url": f"/posts/{job_id}",
            "images": images,
            "metadata": {
                "input_type": input_type,
                "style": selected_style,
                "run_dir": str(run_dir),
                "combo_id": result_dict.get("combo_id"),
                "run_id": result_dict.get("run_id"),
                # For URL-based generation, include original content and source URL
                **(
                    {"original_content": input_value, "source_url": source_url}
                    if input_type == "url"
                    else {}
                ),
            },
        }

        logger.info(
            f"Updating job {job_id} to COMPLETED with result: {len(images)} images"
        )

        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            stage=None,
            progress=100,
            result=result,
        )

        logger.info(f"Generation pipeline completed successfully for job {job_id}")

        # Cleanup temporary files
        try:
            if input_type == "audio" and Path(input_value).exists():
                Path(input_value).unlink()
                # Also try to remove the temp dir if empty
                Path(input_value).parent.rmdir()
            elif input_type != "audio":
                file_name = f"api_job_{job_id}.md"
                sources_dir = repo_paths().content_root / "sources" / "article"
                file_path = sources_dir / file_name
                if file_path.exists():
                    file_path.unlink()
        except Exception as cleanup_err:
            logger.warning(
                f"Failed to cleanup temp files for job {job_id}: {cleanup_err}"
            )

    except asyncio.CancelledError:
        logger.info(f"Generation pipeline canceled for job {job_id}")
        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.CANCELED,
            stage=None,
            progress=0,
        )
    except Exception as e:
        logger.error(f"Generation pipeline failed for job {job_id}: {e}")
        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            stage=None,
            progress=0,
            error=str(e),
        )


@router.post("/generate", response_model=JobResponse)
async def create_generation(
    request: JobCreate,
):
    """Create a new content generation job.

    Args:
        request: Job creation request with input_type, input_value, selected_style

    Returns:
        Created job with job_id
    """
    input_type = request.input_type
    input_value = request.input_value
    selected_style = request.selected_style

    # Validate input
    is_valid, error_message = validate_input(input_type, input_value)
    if not is_valid:
        return JobResponse(
            data=None,
            error={"code": "VALIDATION_ERROR", "message": error_message},
        )

    # For URL input, fetch content first and store original URL
    source_url = None
    if input_type == "url":
        try:
            source_url = input_value  # Store original URL before fetching
            input_value = await fetch_url_content(input_value)
            # Update request with fetched content
            request.input_value = input_value
        except HTTPException as e:
            return JobResponse(
                data=None,
                error={"code": "FETCH_ERROR", "message": str(e.detail)},
            )

    # Create job
    job = job_manager.create_job(request)

    logger.info(f"Created generation job {job.id}")

    # Start background task, passing source_url for URL-based generation
    asyncio.create_task(
        run_generation_pipeline(
            job_id=job.id,
            input_type=input_type,
            input_value=input_value,
            selected_style=selected_style,
            source_url=source_url,
        )
    )

    return JobResponse(data=job, error=None)


@router.post("/generate/audio", response_model=JobResponse)
async def create_generation_from_audio(
    file: UploadFile = File(...),
    selected_style: Optional[str] = None,
):
    """Create a content generation job from audio file upload.

    Args:
        file: Audio file (mp3, wav, etc.)
        selected_style: Optional style preference

    Returns:
        Created job with job_id
    """
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/wave"]
    if file.content_type and file.content_type not in allowed_types:
        return JobResponse(
            data=None,
            error={
                "code": "INVALID_FILE_TYPE",
                "message": f"File type {file.content_type} not allowed. Must be MP3 or WAV",
            },
        )

    # Validate file size (100MB limit)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset position

    if file_size > 100 * 1024 * 1024:
        return JobResponse(
            data=None,
            error={
                "code": "FILE_TOO_LARGE",
                "message": "File size exceeds 100MB limit",
            },
        )

    # For now, we'll store the file and create a job
    # In a real implementation, this would trigger ASR transcription
    try:
        # Save uploaded file temporarily
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp(prefix="narrio-audio-"))
        file_path = temp_dir / file.filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create job with file path
        job_create = JobCreate(
            input_type="audio",
            input_value=str(file_path),
            selected_style=selected_style,
        )
        job = job_manager.create_job(job_create)

        # Start background task (will include ASR transcription)
        asyncio.create_task(
            run_generation_pipeline(
                job_id=job.id,
                input_type="audio",
                input_value=str(file_path),
                selected_style=selected_style,
            )
        )

        return JobResponse(data=job, error=None)

    except Exception as e:
        logger.error(f"Failed to process audio file: {e}")
        return JobResponse(
            data=None,
            error={"code": "UPLOAD_ERROR", "message": str(e)},
        )
