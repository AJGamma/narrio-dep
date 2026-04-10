"""WebSocket endpoints for real-time job updates."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..models.job import JobStatus
from ..services.job_manager import job_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketManager:
    """Manages WebSocket connections per job_id."""

    def __init__(self):
        # Map of job_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = []
        self._connections[job_id].append(websocket)
        logger.info(f"WebSocket client connected for job {job_id}")

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove a WebSocket connection."""
        if job_id in self._connections:
            if websocket in self._connections[job_id]:
                self._connections[job_id].remove(websocket)
            if not self._connections[job_id]:
                del self._connections[job_id]
        logger.info(f"WebSocket client disconnected for job {job_id}")

    async def broadcast(self, job_id: str, message: dict) -> None:
        """Broadcast a message to all connected clients for a job."""
        if job_id not in self._connections:
            logger.debug(f"No WebSocket connections for job {job_id}, message not sent: {message}")
            return

        logger.debug(f"Broadcasting to {len(self._connections[job_id])} client(s) for job {job_id}: {message}")

        disconnected = []
        for websocket in self._connections[job_id]:
            try:
                await websocket.send_json(message)
                logger.debug(f"Message sent successfully to WebSocket for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket for job {job_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, job_id)

    async def send_to_job(self, job_id: str, message: dict) -> bool:
        """Send a message to all clients connected to a job.

        Returns:
            True if at least one client received the message
        """
        if job_id not in self._connections:
            return False

        await self.broadcast(job_id, message)
        return True


# Global WebSocket manager
websocket_manager = WebSocketManager()


# Register broadcast callback with job manager
async def broadcast_job_update(job_id: str, update: dict) -> None:
    """Broadcast job update to WebSocket clients."""
    await websocket_manager.broadcast(job_id, update)


job_manager.set_broadcast_callback(broadcast_job_update)


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job updates."""
    # Verify job exists
    job = job_manager.get_job(job_id)
    if not job:
        await websocket.close(code=404, reason="Job not found")
        return

    await websocket_manager.connect(websocket, job_id)

    # Send initial job status
    initial_status = {
        "type": "initial",
        "job_id": job_id,
        "status": job.status.value,
        "stage": job.stage.value if job.stage else None,
        "progress": job.progress,
        "created_at": job.created_at.isoformat(),
    }
    await websocket.send_json(initial_status)

    try:
        while True:
            # Wait for messages from client (keep-alive, ping, etc.)
            try:
                data = await websocket.receive_text()
                # Handle client messages if needed
                logger.debug(f"Received from WebSocket: {data}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    finally:
        websocket_manager.disconnect(websocket, job_id)
