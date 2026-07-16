from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

# Ensure project root is on sys.path so `app.*` imports resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all active DPDP models so Alembic detects them for autogenerate
from app.db.base import Base  # noqa: E402
import app.models.orm.org  # noqa: F401
import app.models.orm.org_api_key  # noqa: F401
import app.models.orm.dpdp_user  # noqa: F401
import app.models.orm.consent_form  # noqa: F401
import app.models.orm.form_version  # noqa: F401
import app.models.orm.dpdp_consent  # noqa: F401
import app.models.orm.audit_log  # noqa: F401
import app.models.orm.nomination  # noqa: F401
import app.models.orm.async_job  # noqa: F401

target_metadata = Base.metadata


def get_sync_url() -> str:
    explicit = (os.getenv("DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if explicit:
        return explicit.replace("mysql+aiomysql", "mysql+pymysql")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "consent_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


def run_migrations_offline() -> None:
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_sync_url()
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
