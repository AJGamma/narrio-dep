"""SSR content API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models.post import Post
from ...ssr_service import get_scraper, get_source_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ssr-sources")
async def list_ssr_sources() -> dict[str, Any]:
    """List all configured SSR sources and their articles.

    Returns:
        Dictionary containing list of sources with their articles
    """
    try:
        service = get_source_service()
        sources = service.get_all_sources()

        return {
            "data": [
                {
                    "id": source.id,
                    "name": source.name,
                    "avatar": f"/api/ssr/avatars/{Path(source.avatar).name}",
                    "description": source.description,
                    "articles": [
                        {
                            "id": article.id,
                            "title": article.title,
                            "summary": article.summary,
                            "url": article.url,
                        }
                        for article in source.articles
                    ],
                }
                for source in sources
            ],
            "error": None,
        }
    except FileNotFoundError as e:
        logger.warning(f"SSR sources config not found: {e}")
        return {"data": [], "error": {"code": "NOT_FOUND", "message": "SSR sources config not found"}}
    except Exception as e:
        logger.error(f"Error loading SSR sources: {e}")
        return {"data": [], "error": {"code": "INTERNAL_ERROR", "message": str(e)}}


@router.get("/ssr-articles")
async def list_ssr_articles() -> dict[str, Any]:
    """List all articles from all SSR sources.

    Returns:
        Dictionary containing list of articles
    """
    try:
        service = get_source_service()
        articles = service.get_all_articles()

        return {
            "data": [
                {
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary,
                    "url": article.url,
                }
                for article in articles
            ],
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error loading SSR articles: {e}")
        return {"data": [], "error": {"code": "INTERNAL_ERROR", "message": str(e)}}


@router.get("/ssr/avatars/{filename}")
async def get_ssr_avatar(filename: str):
    """Serve SSR source avatar images from local assets directory.

    Args:
        filename: The avatar filename to serve

    Returns:
        The avatar image file
    """
    # Security: only allow image files to prevent path traversal
    if not filename.endswith((".png", ".jpg", ".jpeg", ".svg")):
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Try multiple methods to find the assets directory
    import os

    # Method 1: Use current working directory (where uvicorn was started)
    cwd = Path(os.getcwd())
    avatar_path = cwd / "assets" / "images" / filename

    # Method 2: Fall back to relative to this file
    if not avatar_path.exists():
        this_file_dir = Path(__file__).parent
        backend_root = this_file_dir.parent.parent.parent.parent
        avatar_path = backend_root / "assets" / "images" / filename
        logger.info(f"Trying fallback path: {avatar_path}")

    # Check if file exists
    if not avatar_path.exists():
        logger.error(f"Avatar file not found: {avatar_path}, cwd={cwd}")
        raise HTTPException(status_code=404, detail=f"Avatar not found: {filename}")

    logger.info(f"Serving avatar: {avatar_path}")
    return FileResponse(avatar_path, media_type="image/png")


@router.post("/ssr/scrape")
async def scrape_ssr_content(data: dict[str, Any]) -> dict[str, Any]:
    """Scrape content from an SSR URL.

    Args:
        data: Dictionary containing 'url' key with the URL to scrape

    Returns:
        Dictionary containing scraped content:
        - title: Page title
        - content: Main content text
        - cover: Cover image URL
        - url: Original URL
    """
    url = data.get("url")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        scraper = get_scraper()
        content = await scraper.scrape_url(url)

        return {
            "data": {
                "title": content["title"],
                "content": content["content"],
                "cover": content["cover"],
                "url": content["url"],
                "input_type": "url",
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape content: {str(e)}")


@router.post("/ssr/scrape-to-post")
async def scrape_ssr_to_post(data: dict[str, Any]) -> dict[str, Any]:
    """Scrape content from an SSR URL and convert to Post format.

    This endpoint is designed to integrate with the existing generation pipeline.

    Args:
        data: Dictionary containing 'url' key with the URL to scrape

    Returns:
        Post object ready for further processing
    """
    url = data.get("url")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        scraper = get_scraper()
        content = await scraper.scrape_url(url)

        post = Post(
            id=f"ssr_{hash(url) % 1000000}",
            title=content["title"],
            content=content["content"],
            content_type="article",
            images=[{"url": content["cover"], "alt": content["title"]}],
            audio_url=None,
            author=None,
            metadata={"source_url": url, "scraped": True},
        )

        return {
            "data": post,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape content: {str(e)}")
