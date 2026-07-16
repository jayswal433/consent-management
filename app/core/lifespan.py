from __future__ import annotations

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    yield
