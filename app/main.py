from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import router as api_router
from app.graphql.router import router as graphql_router
from app.web.router import router as web_router

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan handler.
    - On startup: starts analyzer listener workers (BC-5150, BS-240, etc.)
    - On shutdown: gracefully stops all listener tasks
    """
    # Import here to avoid circular imports at module load time
    from app.services.analyzer_ingestion_service import (
        start_analyzer_workers,
        stop_analyzer_workers,
    )
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Starting analyzer listener workers...")
    try:
        tasks = await start_analyzer_workers()
        logger.info("Analyzer workers started: %d listeners active", len(tasks))
    except Exception:
        logger.exception("Failed to start analyzer workers — continuing without them")

    yield  # Application runs here

    logger.info("Stopping analyzer listener workers...")
    try:
        await stop_analyzer_workers()
    except Exception:
        logger.exception("Error stopping analyzer workers")


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    # CORS HEADERS
    origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    app.include_router(web_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(graphql_router)

    return app


# templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
app = create_app()