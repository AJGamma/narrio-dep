"""Post data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Post(BaseModel):
    """Post model representing generated content."""

    id: str = Field(..., description="Unique post identifier")
    title: str = Field(..., description="Post title")
    content: Optional[str] = Field(default=None, description="Post content text")
    content_type: str = Field(default="article", description="Content type: article or podcast")

    # Images
    images: list[dict[str, Any]] = Field(default_factory=list, description="Generated images")

    # Audio
    audio_url: Optional[str] = Field(default=None, description="Audio file URL or path")

    # Author
    author: Optional[str] = Field(default=None, description="Author name")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Engagement
    like_count: int = Field(default=0, description="Number of likes")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        use_enum_values = True


class PostCreate(BaseModel):
    """Request model for creating a post."""

    title: str
    content: str
    content_type: str = "article"
    images: list[dict[str, Any]] = Field(default_factory=list)
    audio_url: Optional[str] = None
    author: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PostResponse(BaseModel):
    """Response model for post operations."""

    data: Optional[Post] = Field(default=None, description="Post data")
    error: Optional[dict[str, Any]] = Field(default=None, description="Error details")


class PostListResponse(BaseModel):
    """Response model for listing posts."""

    data: list[Post] = Field(default_factory=list, description="List of posts")
    total: int = Field(default=0, description="Total post count")
    limit: int = Field(default=20, description="Page limit")
    offset: int = Field(default=0, description="Page offset")
    error: Optional[dict[str, Any]] = Field(default=None, description="Error details")
