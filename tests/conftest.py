"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import os

import pytest

# Runtime sessions require Redis. Default to logical DB 15 so tests do not wipe dev keys on DB 0.
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")


async def _reset_redis_for_test() -> None:
    from app.core.runtime_session_redis import (
        get_runtime_redis_client,
        reset_runtime_redis_client,
    )

    await reset_runtime_redis_client()
    client = get_runtime_redis_client()
    await client.flushdb()
    await reset_runtime_redis_client()


@pytest.fixture(autouse=True)
def reset_runtime_redis_singleton() -> None:
    """Clear singleton and flush test Redis DB between tests."""
    asyncio.run(_reset_redis_for_test())
    yield
    asyncio.run(_reset_redis_for_test())
