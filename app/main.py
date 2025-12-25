from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import router as api_router
from app.graphql.router import router as graphql_router
from app.web.router import router as web_router

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.APP_NAME)

    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    app.include_router(web_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(graphql_router)

    return app

app = create_app()
