"""Post retrieval API endpoints."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query

from ..models.post import Post, PostListResponse

router = APIRouter()


def get_output_dirs() -> list[Path]:
    """Get all output directories to scan for posts."""
    # Look for narrio output directories
    # Typical structure: narrio-frontend/public/posts or similar
    possible_roots = [
        Path.cwd().parent / "narrio-frontend" / "public" / "posts",
        Path.cwd() / "output",
        Path.home() / "narrio-output",
    ]

    dirs = []
    for root in possible_roots:
        if root.exists():
            dirs.append(root)

    # If no standard dirs found, try to find any "output" or "posts" directories
    if not dirs:
        # Scan current directory and parent for output directories
        for pattern in ["**/output", "**/posts", "**/generated"]:
            for match in Path.cwd().parent.glob(pattern):
                if match.is_dir():
                    dirs.append(match)

    return dirs


def scan_post_files() -> list[Path]:
    """Scan output directories for post files."""
    output_dirs = get_output_dirs()
    post_files = []

    for output_dir in output_dirs:
        # Look for markdown files and JSON metadata
        for pattern in ["**/*.md", "**/*.json", "**/post_*/"]:
            for match in output_dir.glob(pattern):
                if match.is_file() or match.is_dir():
                    post_files.append(match)

    return post_files


def parse_post_from_file(file_path: Path) -> Optional[Post]:
    """Parse a post from a file.

    This is a simplified parser - adjust based on actual file format.
    """
    try:
        if file_path.suffix == ".json":
            import json

            data = json.loads(file_path.read_text())
            return Post(
                id=data.get("id", file_path.stem),
                title=data.get("title", "Untitled"),
                content=data.get("content"),
                content_type=data.get("content_type", "article"),
                images=data.get("images", []),
                audio_url=data.get("audio_url"),
                author=data.get("author"),
                created_at=datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow(),
                like_count=data.get("like_count", 0),
                metadata=data,
            )
        elif file_path.suffix == ".md":
            # Parse markdown file
            content = file_path.read_text()

            # Extract title from frontmatter or first heading
            title = "Untitled"
            frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                title_match = re.search(r"title:\s*(.+)", frontmatter)
                if title_match:
                    title = title_match.group(1).strip()

            # Look for first heading
            heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if heading_match and title == "Untitled":
                title = heading_match.group(1)

            # Look for images
            images = []
            for img_match in re.finditer(r"!\[(.*?)\]\((.*?)\)", content):
                images.append({"alt": img_match.group(1), "url": img_match.group(2)})

            return Post(
                id=file_path.stem,
                title=title,
                content=content[:1000] if len(content) > 1000 else content,
                content_type="article",
                images=images,
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                metadata={"file_path": str(file_path)},
            )
        elif file_path.is_dir():
            # Directory-based post
            return Post(
                id=file_path.name,
                title=file_path.name.replace("_", " ").title(),
                content_type="article",
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                metadata={"directory": str(file_path)},
            )
    except Exception as e:
        print(f"Error parsing post from {file_path}: {e}")

    return None


class PostRepository:
    """Repository for scanning and indexing generated content."""

    def __init__(self):
        self._cache: Optional[list[Post]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Cache for 1 minute

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_time is None:
            return False

        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < self._cache_ttl_seconds

    def _refresh_cache(self) -> None:
        """Refresh the post cache."""
        post_files = scan_post_files()
        posts = []

        for file_path in post_files:
            post = parse_post_from_file(file_path)
            if post:
                posts.append(post)

        # Sort by created_at descending
        posts.sort(key=lambda p: p.created_at, reverse=True)

        self._cache = posts
        self._cache_time = datetime.utcnow()

    def get_all_posts(
        self,
        limit: int = 20,
        offset: int = 0,
        content_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> tuple[list[Post], int]:
        """Get all posts with filtering and pagination.

        Args:
            limit: Maximum number of posts to return
            offset: Number of posts to skip
            content_type: Filter by content type (article/podcast)
            from_date: Filter posts created after this date (YYYY-MM-DD)
            to_date: Filter posts created before this date (YYYY-MM-DD)
            search_query: Full-text search query

        Returns:
            Tuple of (posts list, total count)
        """
        if not self._is_cache_valid():
            self._refresh_cache()

        posts = self._cache or []

        # Filter by content type
        if content_type:
            posts = [p for p in posts if p.content_type == content_type]

        # Filter by date range
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d")
                posts = [p for p in posts if p.created_at >= from_dt]
            except ValueError:
                pass

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d")
                posts = [p for p in posts if p.created_at <= to_dt]
            except ValueError:
                pass

        # Full-text search
        if search_query:
            query_lower = search_query.lower()
            posts = [
                p
                for p in posts
                if query_lower in p.title.lower()
                or (p.content and query_lower in p.content.lower())
            ]

        total = len(posts)
        paginated = posts[offset : offset + limit]

        return paginated, total

    def get_post_by_id(self, post_id: str) -> Optional[Post]:
        """Get a single post by ID.

        Args:
            post_id: Post identifier

        Returns:
            Post if found, None otherwise
        """
        if not self._is_cache_valid():
            self._refresh_cache()

        for post in self._cache or []:
            if post.id == post_id:
                return post

        # Try to find directly
        output_dirs = get_output_dirs()
        for output_dir in output_dirs:
            # Try as JSON file
            json_file = output_dir / f"{post_id}.json"
            if json_file.exists():
                return parse_post_from_file(json_file)

            # Try as markdown file
            md_file = output_dir / f"{post_id}.md"
            if md_file.exists():
                return parse_post_from_file(md_file)

            # Try as directory
            dir_path = output_dir / post_id
            if dir_path.is_dir():
                return parse_post_from_file(dir_path)

        return None


# Global repository instance
post_repository = PostRepository()


@router.get("/posts", response_model=PostListResponse)
async def list_posts(
    limit: int = Query(default=20, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    type: Optional[str] = Query(default=None, description="Filter by content type"),
    from_date: Optional[str] = Query(default=None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="Filter to date (YYYY-MM-DD)"),
    q: Optional[str] = Query(default=None, description="Search query"),
):
    """List posts with pagination and filtering."""
    posts, total = post_repository.get_all_posts(
        limit=limit,
        offset=offset,
        content_type=type,
        from_date=from_date,
        to_date=to_date,
        search_query=q,
    )

    return PostListResponse(
        data=posts,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/posts/{post_id}")
async def get_post(post_id: str):
    """Get a single post by ID."""
    post = post_repository.get_post_by_id(post_id)

    if not post:
        return {
            "data": None,
            "error": {"code": "NOT_FOUND", "message": f"Post {post_id} not found"},
        }

    return {"data": post, "error": None}
