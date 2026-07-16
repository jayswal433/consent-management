"""CORS configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Matches localhost, loopback, and private/LAN IP origins (with optional port).
_DEV_ORIGIN_REGEX = (
    r"https?://"
    r"(localhost|127\.0\.0\.1|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"
    r"(:\d+)?$"
)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def get_cors_middleware_kwargs() -> dict:
    """Build kwargs for Starlette CORSMiddleware from environment."""
    origins = _parse_csv(os.getenv("CORS_ORIGINS", "*"))
    methods = _parse_csv(os.getenv("CORS_ALLOW_METHODS", "*")) or ["*"]
    headers = _parse_csv(os.getenv("CORS_ALLOW_HEADERS", "*")) or ["*"]
    allow_credentials = (
        os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    )

    kwargs: dict = {
        "allow_methods": methods,
        "allow_headers": headers,
        "allow_credentials": allow_credentials,
        "expose_headers": ["*"],
    }

    wildcard_origins = not origins or "*" in origins

    if wildcard_origins and allow_credentials:
        # Browsers reject Allow-Origin: * when credentials are included.
        # Use a regex that matches any origin so the server echoes it back.
        kwargs["allow_origins"] = []
        kwargs["allow_origin_regex"] = ".*"
    elif wildcard_origins:
        kwargs["allow_origins"] = ["*"]
    else:
        kwargs["allow_origins"] = origins

    return kwargs
