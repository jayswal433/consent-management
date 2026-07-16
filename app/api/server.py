from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api.v1.router import create_v1_router
from app.core.config.cors_config import get_cors_middleware_kwargs
from app.core.logging import setup_logging
from app.core.middleware import (
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
    setup_error_handlers,
)

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Apply all pending Alembic migrations synchronously at startup."""
    if os.getenv("RUN_MIGRATIONS_ON_STARTUP", "true").lower() != "true":
        logger.info("Skipping database migrations (RUN_MIGRATIONS_ON_STARTUP=false).")
        return

    try:
        from alembic import command
        from alembic.config import Config

        alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
        if not alembic_ini.exists():
            logger.error("alembic.ini not found at %s — skipping migrations.", alembic_ini)
            return

        cfg = Config(str(alembic_ini))
        command.upgrade(cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception:
        # Log the full traceback but do not re-raise. A migration failure
        # (e.g. DB not yet reachable, already up-to-date) must not crash
        # the application process — the service should still start and
        # serve health-check requests so orchestrators can detect it.
        logger.exception(
            "Database migration failed — the application will start anyway. "
            "Check DB connectivity and re-run migrations manually if needed."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Configure logging in the server subprocess (uvicorn spawns a fresh process
    # when reload=True, so setup_logging() in asgi.py only runs in the parent).
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
    _run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="DPDP Consent Management API",
        version="1.0.0",
        description="DPDP Act 2023-compliant Consent Management microservice.",
        lifespan=lifespan,
        root_path_in_servers=False,
    )
    setup_error_handlers(app)

    app.include_router(create_v1_router())

    # @app.get("/docs", include_in_schema=False)
    # async def swagger_ui() -> HTMLResponse:
    #     return get_swagger_ui_html(
    #         openapi_url="/openapi.json",
    #         title="DPDP Consent Management API – Swagger UI",
    #         swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    #         swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    #     )

    # @app.get("/redoc", include_in_schema=False)
    # async def redoc_ui() -> HTMLResponse:
    #     return get_redoc_html(
    #         openapi_url="/openapi.json",
    #         title="DPDP Consent Management API – ReDoc",
    #         redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
    #     )

    # Last added = outermost. RequestLoggingMiddleware runs first so every
    # request is logged, including CORS preflight and dependency failures.
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(CORSMiddleware, **get_cors_middleware_kwargs())
    app.add_middleware(RequestLoggingMiddleware)

    return app


app = create_app()
