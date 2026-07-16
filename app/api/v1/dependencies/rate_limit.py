from fastapi import Request


async def rate_limit(_request: Request) -> None:
    """
    Placeholder dependency for boilerplate structure parity.

    Intentionally no-op to preserve existing functionality.

    TODO(CMP-RATE-001): Add rate limiting for public SDK/consent endpoints
    (sessions, config, consents). Tracked for production hardening.
    """
    return None
