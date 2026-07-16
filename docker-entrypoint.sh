#!/bin/sh
# Runs Alembic migrations exactly once before the server starts.
# This prevents all uvicorn workers from racing to run migrations in parallel.

echo "==> Running database migrations..."
python - <<'PYEOF'
import sys
from pathlib import Path

ini = Path("alembic.ini")
if not ini.exists():
    print("alembic.ini not found — skipping migrations.", file=sys.stderr)
    sys.exit(0)

from alembic import command
from alembic.config import Config

try:
    cfg = Config(str(ini))
    command.upgrade(cfg, "head")
    print("Migrations applied successfully.")
except Exception as exc:
    # Non-fatal: log and continue so the server still starts.
    print(f"Migration warning (non-fatal): {exc}", file=sys.stderr)
PYEOF

echo "==> Starting application server..."
exec python asgi.py --env prod
