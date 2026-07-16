"""Redis-backed runtime CMP session storage (replaces consent_sessions rows)."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

SESSION_KEY_PREFIX = "cmp:rt_session:"

_client: Any = None


def _redis_url() -> str:
    return (os.getenv("REDIS_URL") or "").strip()


def _build_client() -> Any:
    url = _redis_url()
    if not url:
        raise RuntimeError(
            "REDIS_URL is not set. Set it to your Redis server, e.g. "
            "redis://127.0.0.1:6379/0"
        )
    import redis.asyncio as redis_mod

    return redis_mod.from_url(url, decode_responses=True)


def get_runtime_redis_client() -> Any:
    """Singleton async Redis client."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


async def reset_runtime_redis_client() -> None:
    """Close and clear singleton (for tests)."""
    global _client
    if _client is None:
        return
    try:
        await _client.aclose()
    except Exception:
        pass
    _client = None


async def get_runtime_redis() -> AsyncIterator[Any]:
    yield get_runtime_redis_client()


def session_redis_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


async def save_runtime_session(
    redis: Any,
    *,
    session_id: str,
    user_id: str,
    template_id: str,
    domain: str,
    jti: str,
    ttl_seconds: int,
) -> None:
    payload = json.dumps(
        {
            "user_id": user_id,
            "template_id": template_id,
            "domain": domain.lower(),
            "jti": jti,
        },
        separators=(",", ":"),
    )
    await redis.set(session_redis_key(session_id), payload, ex=ttl_seconds)


async def load_runtime_session(redis: Any, session_id: str) -> dict[str, Any] | None:
    raw = await redis.get(session_redis_key(session_id))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def delete_runtime_session(redis: Any, session_id: str) -> int:
    return int(await redis.delete(session_redis_key(session_id)))
