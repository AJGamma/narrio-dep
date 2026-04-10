"""Styles API endpoint for listing available visual styles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


def get_styles_root() -> Path:
    """Get the root directory for style definitions.

    Looks for styles in:
    1. Backend assets/styles/ directory
    2. Falls back to a configurable path
    """
    # Try to find styles in backend assets
    backend_root = Path(__file__).parent.parent.parent
    styles_dir = backend_root / "assets" / "styles"

    if styles_dir.exists():
        return styles_dir

    # Fallback to current directory
    return Path.cwd() / "assets" / "styles"


@router.get("/styles")
async def list_styles() -> dict[str, Any]:
    """List all available visual styles.

    Returns:
        List of style definitions with:
        - id: Style directory name (e.g., "OpenAI", "Anthropic")
        - name: Human-readable name from style.json or directory name
        - cover: URL to ref.png preview image
        - description: Description from style.json
    """
    styles_root = get_styles_root()

    if not styles_root.exists():
        logger.warning(f"Styles directory not found: {styles_root}")
        return {
            "data": [],
            "error": {"code": "NOT_FOUND", "message": "Styles directory not found"}
        }

    styles = []

    for style_dir in styles_root.iterdir():
        if not style_dir.is_dir():
            continue

        style_id = style_dir.name
        ref_png = style_dir / "ref.png"
        style_json = style_dir / "style.json"

        # Read style.json if exists
        name = style_id
        description = ""

        if style_json.exists():
            try:
                style_data = json.loads(style_json.read_text())
                name = style_data.get("name", style_id)
                description = style_data.get("description", "")
            except Exception as e:
                logger.warning(f"Failed to read style.json for {style_id}: {e}")

        # Build cover URL - serve ref.png from assets
        # For now, use a relative path that frontend can resolve
        cover_url = f"/api/assets/styles/{style_id}/ref.png"

        styles.append({
            "id": style_id,
            "name": name,
            "cover": cover_url,
            "description": description,
        })

    # Sort by name
    styles.sort(key=lambda s: s["name"])

    return {
        "data": styles,
        "error": None,
    }


@router.get("/assets/styles/{style_id}/ref.png")
async def get_style_preview(style_id: str):
    """Serve style preview image (ref.png).

    Args:
        style_id: Style directory name

    Returns:
        PNG image file
    """
    from fastapi.responses import FileResponse

    styles_root = get_styles_root()
    style_dir = styles_root / style_id
    ref_png = style_dir / "ref.png"

    if not ref_png.exists():
        return {"error": {"code": "NOT_FOUND", "message": f"Preview image not found for style {style_id}"}}

    return FileResponse(
        str(ref_png),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"}
    )
