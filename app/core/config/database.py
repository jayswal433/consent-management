import logging
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

load_dotenv()

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    explicit = (os.getenv("DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        return explicit
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "consent_db")
    url = (
        "mysql+aiomysql://"
        f"{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    )
    logger.debug("DB connecting to %s:%s/%s as %s", host, port, name, user)
    return url


DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    future=True,
    # Test connections before use — critical in containers where the DB host
    # may be a remote server that drops idle connections.
    pool_pre_ping=True,
    # Recycle connections after 30 minutes to avoid "MySQL has gone away".
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
