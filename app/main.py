from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import router as api_router
from app.graphql.router import router as graphql_router
from app.web.router import router as web_router


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.APP_NAME)

    # CORS HEADERS
    origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    app.include_router(web_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(graphql_router)

    return app


# templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
app = create_app()
