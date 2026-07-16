"""HTTP request/response logging middleware with timing and body capture."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_BODY_METHODS = {"POST", "PUT", "PATCH"}
_MAX_BODY_LOG = 2_000  # characters
_LOGGABLE_CONTENT_TYPES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "text/",
)


def _should_log_body(request: Request) -> bool:
    ct = request.headers.get("content-type", "")
    return any(ct.startswith(t) for t in _LOGGABLE_CONTENT_TYPES)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every incoming request and its response status with timing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()

        client = request.client.host if request.client else "-"
        method = request.method
        path = request.url.path
        query = f"?{request.url.query}" if request.url.query else ""
        http_version = request.scope.get("http_version", "1.1")

        # Capture body snippet for mutation methods with text payloads.
        body_hint = ""
        if method in _BODY_METHODS and _should_log_body(request):
            try:
                raw = await request.body()
                if raw:
                    snippet = raw[:_MAX_BODY_LOG].decode("utf-8", errors="replace")
                    suffix = " [truncated]" if len(raw) > _MAX_BODY_LOG else ""
                    body_hint = f"  body={snippet}{suffix}"
            except Exception:
                body_hint = "  body=<unreadable>"

        logger.info(
            "→ %s %s%s HTTP/%s  client=%s%s",
            method, path, query, http_version, client, body_hint,
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1_000
            logger.exception(
                "✗ %s %s%s  client=%s  status=500  %.1fms",
                method, path, query, client, elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1_000
        status = response.status_code
        log_level = logging.WARNING if status >= 400 else logging.INFO
        logger.log(
            log_level,
            "← %s %s%s  client=%s  status=%d  %.1fms",
            method, path, query, client, status, elapsed_ms,
        )
        return response
