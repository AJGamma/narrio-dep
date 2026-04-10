"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for connectivity testing.

    Returns:
        JSON response with status field
    """
    return {"data": {"status": "healthy"}, "error": None}
