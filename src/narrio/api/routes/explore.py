"""Explore content API endpoint for serving explore content files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_explore_content_root() -> Path:
    """Get the root directory for explore content.

    Looks for explore-content in:
    1. Backend root directory (narrio-backend/explore-content/)
    """
    # Backend root is parent of src/narrio
    backend_root = Path(__file__).parent.parent.parent
    explore_dir = backend_root / "explore-content"

    if explore_dir.exists():
        return explore_dir

    # Fallback to current working directory
    return Path.cwd() / "explore-content"


@router.get("/explore/directories")
async def list_explore_directories() -> dict[str, Any]:
    """List all explore content directories with their available files.

    Returns:
        List of directory info objects containing directory name and available markdown files
    """
    explore_root = get_explore_content_root()

    if not explore_root.exists():
        logger.warning(f"Explore content directory not found: {explore_root}")
        return {
            "data": [],
            "error": {"code": "NOT_FOUND", "message": "Explore content directory not found"}
        }

    directories = []
    for item in explore_root.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # Find all markdown files in the directory
            md_files = [f.name for f in item.iterdir() if f.is_file() and f.suffix.lower() == ".md"]
            # Check if info.json exists
            has_info = (item / "info.json").exists()
            # Check if avatar.png exists
            has_avatar = (item / "avatar.png").exists()
            # Check for numbered images
            images = []
            for i in range(20):
                img_path = item / f"{i}.png"
                if img_path.exists():
                    images.append(f"{i}.png")

            directories.append({
                "name": item.name,
                "md_files": md_files,
                "has_info": has_info,
                "has_avatar": has_avatar,
                "images": images,
            })

    # Sort alphabetically by name
    directories.sort(key=lambda x: x["name"])

    return {
        "data": directories,
        "error": None,
    }


@router.get("/explore-content/{dir_name}/info.json")
async def get_explore_info(dir_name: str):
    """Get info.json for an explore content directory.

    Args:
        dir_name: Directory name (URL decoded by FastAPI)

    Returns:
        JSON file with title and author
    """
    explore_root = get_explore_content_root()
    content_dir = explore_root / dir_name
    info_json = content_dir / "info.json"

    if not info_json.exists():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": f"info.json not found for {dir_name}"}}
        )

    return FileResponse(
        str(info_json),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/explore-content/{dir_name}/{file_name:path}")
async def get_explore_file(dir_name: str, file_name: str):
    """Serve explore content files (images, markdown, etc.).

    Args:
        dir_name: Directory name
        file_name: File name (can include subpaths)

    Returns:
        File content (image, markdown, etc.)
    """
    explore_root = get_explore_content_root()
    content_dir = explore_root / dir_name
    file_path = content_dir / file_name

    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": f"File not found: {dir_name}/{file_name}"}}
        )

    # Determine media type based on extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".md": "text/markdown",
        ".json": "application/json",
        ".txt": "text/plain",
    }

    media_type = media_types.get(suffix, "application/octet-stream")

    # Cache images for longer, text files for shorter time
    cache_age = 31536000 if suffix in [".png", ".jpg", ".jpeg", ".webp", ".svg"] else 3600

    return FileResponse(
        str(file_path),
        media_type=media_type,
        headers={"Cache-Control": f"public, max-age={cache_age}"}
    )
