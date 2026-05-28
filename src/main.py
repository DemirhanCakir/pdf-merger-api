import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from src.config import get_settings
from src.db import create_all, get_engine, init_engine
from src.routers import files, health, merge
from src.services import s3_client
from src.telemetry import setup_otel


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    init_engine()
    create_all()
    try:
        s3_client.ensure_bucket()
    except Exception:
        logging.getLogger(__name__).warning(
            "Could not ensure S3 bucket on startup; will retry on first request"
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="REST API that merges multiple PDF files into one.",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(files.router)
    app.include_router(merge.router)

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    setup_otel(app, get_engine())

    return app


app = create_app()
