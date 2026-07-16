"""
Global error handling (middleware + FastAPI exception handlers),
aligned with boilerplate layout.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.responses import StandardResponse
from app.core.utils import constant_variable

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions and returns JSON
    in the app's standard error shape.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        try:
            return await call_next(request)
        except HTTPException as exc:
            return await self._handle_http_exception(request, exc)
        except RequestValidationError as exc:
            return await self._handle_validation_error(request, exc)
        except Exception as exc:
            return await self._handle_general_exception(request, exc)

    async def _handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> Response:
        logger.warning(
            "HTTP %d [%s %s%s] — %s",
            exc.status_code,
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            exc.detail,
        )
        message = (
            exc.detail if isinstance(exc.detail, str) else "Request failed."
        )
        return StandardResponse(
            status_code=exc.status_code,
            message=message,
        ).make

    async def _handle_validation_error(
        self, request: Request, exc: RequestValidationError
    ) -> Response:
        errors = exc.errors()
        field_detail = "; ".join(
            f"[{' -> '.join(str(loc) for loc in e['loc'])}] {e['msg']}"
            for e in errors
        )
        logger.warning(
            "Validation Error [%s %s%s]: %d field(s) failed — %s",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            len(errors),
            field_detail,
        )
        formatted_errors = [
            {
                "field": " -> ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        message = constant_variable.GENERAL_MESSAGES["VALIDATION_ERROR"]
        if exc.errors():
            first = exc.errors()[0].get("msg")
            if isinstance(first, str):
                message = first
        return StandardResponse.validation_error(
            message=message,
            data={"errors": formatted_errors},
        ).make

    async def _handle_general_exception(
        self, request: Request, exc: Exception
    ) -> Response:
        logger.error(
            "Unhandled Exception [%s %s%s] — %s: %s",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return StandardResponse.internal_error(
            message=constant_variable.GENERAL_MESSAGES["INTERNAL_ERROR"],
        ).make


def setup_error_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on a FastAPI app
    (main gateway or mounted v1 app).
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> Response:
        logger.warning(
            "HTTP %d [%s %s%s] — %s",
            exc.status_code,
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            exc.detail,
        )
        message = (
            exc.detail if isinstance(exc.detail, str) else "Request failed."
        )
        return StandardResponse(
            status_code=exc.status_code,
            message=message,
        ).make

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Response:
        errors = exc.errors()
        field_detail = "; ".join(
            f"[{' -> '.join(str(loc) for loc in e['loc'])}] {e['msg']}"
            for e in errors
        )
        logger.warning(
            "Validation Error [%s %s%s]: %d field(s) failed — %s",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            len(errors),
            field_detail,
        )
        formatted_errors = [
            {
                "field": " -> ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        message = constant_variable.GENERAL_MESSAGES["VALIDATION_ERROR"]
        if exc.errors():
            first = exc.errors()[0].get("msg")
            if isinstance(first, str):
                message = first
        return StandardResponse.validation_error(
            message=message,
            data={"errors": formatted_errors},
        ).make

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> Response:
        logger.error(
            "Unhandled Exception [%s %s%s] — %s: %s",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return StandardResponse.internal_error(
            message=constant_variable.GENERAL_MESSAGES["INTERNAL_ERROR"],
        ).make
