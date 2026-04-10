"""FastAPI application for Narrio content generation API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_config

# Configure logging for the FastAPI application when run via uvicorn
raw_level = os.getenv("NARRIO_LOG_LEVEL", "INFO").upper().strip()
log_level = getattr(logging, raw_level, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup
        logger.info("Starting Narrio API server")
        try:
            config = load_config()
            logger.info(f"Loaded config from .narrio.yaml")
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
        yield
        # Shutdown
        logger.info("Shutting down Narrio API server")

    app = FastAPI(
        title="Narrio API",
        description="AI content generation pipeline API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    allowed_origins = get_allowed_origins()
    logger.info(f"Configured CORS for origins: {allowed_origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from .api.routes import health, posts, generation, jobs, websocket, ssr, styles, explore

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(posts.router, prefix="/api", tags=["posts"])
    app.include_router(generation.router, prefix="/api", tags=["generation"])
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])
    app.include_router(websocket.router)
    app.include_router(ssr.router, prefix="/api", tags=["ssr"])
    app.include_router(styles.router, prefix="/api", tags=["styles"])
    app.include_router(explore.router, prefix="/api", tags=["explore"])

    return app


def get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from config or environment."""
    # Environment variable takes precedence
    env_origins = os.getenv("NARRIO_ALLOWED_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    # Default development origins
    default_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Try to load from config
    try:
        config = load_config()
        if hasattr(config, "allowed_origins") and config.allowed_origins:
            return config.allowed_origins
    except Exception:
        pass

    return default_origins


# Create app instance
app = create_app()
