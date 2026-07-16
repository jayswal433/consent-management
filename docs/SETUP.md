# Developer Setup Guide

This guide walks you through setting up the EveryCRED DPDP Consent Management Backend on a local machine. The service is a FastAPI 0.125 application targeting Python 3.12, backed by MySQL 8 for persistence and Redis 7 for async job tracking.

## Prerequisites

You will need the following installed before you begin:

**Python 3.12** is required. The project uses `match` statements and other 3.12-era syntax, so earlier versions will not work. Use [pyenv](https://github.com/pyenv/pyenv) or the official installer to pin your interpreter.

**Poetry** manages the virtual environment and dependency lockfile. Install it with the [official installer](https://python-poetry.org/docs/#installation) rather than pip, so it remains isolated from your system Python.

**MySQL 8** is the primary database. You can run it natively or via Docker. The async driver used is `aiomysql`, which expects MySQL 8's default `utf8mb4` charset.

**Redis 7** is used by background job modules and runtime session tracking. A plain `redis-server` on the default port is sufficient for local development.

**Git** is needed to clone the repository. SSH access to the remote is assumed.

## Getting the Code

```bash
git clone <repository-url>
cd everycred-consent-management-backend
```

All subsequent commands assume your working directory is the project root.

## Installing Dependencies

```bash
poetry install
```

Poetry reads `pyproject.toml` and `poetry.lock` to create a fully reproducible virtual environment under `.venv`. This installs the application runtime (FastAPI, SQLAlchemy, Alembic, PyJWT, cryptography, boto3, redis, and so on) as well as the development tooling (pytest, httpx, pytest-asyncio). After this step, activate the environment with `poetry shell` or prefix every command with `poetry run`.

## Environment Configuration

The application reads its configuration entirely from environment variables, which are loaded from a `.env` file in the project root at startup. A minimal template is provided as `local.env`:

```bash
cp local.env .env
```

Open `.env` in your editor and fill in each variable group.

### Server

| Variable | Default | Purpose |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | The interface uvicorn binds to |
| `SERVER_PORT` | `9000` | The TCP port |
| `LOG_LEVEL` | `DEBUG` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

For local development, the defaults from `local.env` are fine. In production you would typically set `LOG_LEVEL=INFO`.

### Database

The service accepts either a full connection string or individual parts.

If you provide `DB_URL` (or `DATABASE_URL`), it takes precedence and the individual variables are ignored. The format is:

```
mysql+aiomysql://user:password@host:port/dbname?charset=utf8mb4
```

Alternatively, set the individual variables:

| Variable | Default | Purpose |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | — | Database user |
| `DB_PASSWORD` | — | Database password |
| `DB_NAME` | `consent_db` | Database name |

### JWT

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | — | Signing secret; use a strong random value |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Access token lifetime (24 hours) |

### Redis

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379` | Connection URL for the Redis instance |

### Encryption Keys

These two keys are critical for DPDP compliance and must be generated before the service can handle any PII.

| Variable | Purpose |
|---|---|
| `DPDP_DEK_HEX` | 32-byte AES-256 data encryption key (stored as 64 hex characters) |
| `DPDP_HMAC_KEY_HEX` | 32-byte HMAC-SHA256 key used to sign consent receipt tokens (stored as 64 hex characters) |

Generate both keys using Python's cryptographically secure random generator:

```python
import secrets
print(secrets.token_hex(32))  # run this twice — once for DEK, once for HMAC
```

Copy each output to the respective variable. **Never commit these values to source control.** Treat them as production secrets equivalent to a private key.

### AWS (Optional)

AWS integration is required only when you want consent receipts or audit exports to be stored in S3. For local development this can be left empty and the service will fall back to local storage.

| Variable | Purpose |
|---|---|
| `AWS_REGION` | AWS region (e.g. `ap-south-1`) |
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `S3_BUCKET_NAME` | Target bucket name |

### Migration Control

| Variable | Default | Purpose |
|---|---|---|
| `RUN_MIGRATIONS_ON_STARTUP` | `true` | When `true`, Alembic runs `upgrade head` automatically during the FastAPI lifespan startup event |

This is safe to leave enabled in development. In production, you may prefer to run migrations as a pre-deploy step and set this to `false`.

## Database Setup

Create the database in MySQL before the first run:

```sql
CREATE DATABASE consent_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then apply all Alembic migrations to bring the schema to the current state:

```bash
alembic upgrade head
```

If `RUN_MIGRATIONS_ON_STARTUP=true`, the service runs this command automatically on startup using the `alembic.ini` in the project root. You still need to ensure the database exists before the first launch.

## Running the Server

The application entrypoint is `asgi.py`, which wraps uvicorn in a Click CLI:

```bash
python asgi.py --env local
```

For verbose output during development:

```bash
python asgi.py --env local --debug
```

The `--env` flag controls which environment label is set internally (`local`, `dev`, or `prod`). The `--debug` flag sets the log level to `DEBUG` regardless of the `LOG_LEVEL` environment variable. The server starts on the host and port specified in your `.env` file. The OpenAPI docs are available at `http://localhost:9000/docs` once the server is running.

## Docker Setup

If you prefer to run the full stack in containers, use Docker Compose. This starts the application, MySQL, and Redis together:

```bash
docker-compose up --build
```

On subsequent runs without code changes, `docker-compose up` (without `--build`) is faster. The Compose file maps the same port configured in `SERVER_PORT`.

## Running Tests

The test suite uses pytest with async support via `pytest-asyncio`. Run the full suite from the project root:

```bash
pytest
```

For verbose output that shows individual test names:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_auth_api.py
```

The `conftest.py` sets up an in-memory SQLite database for most tests so you do not need a running MySQL instance for the unit test suite. Tests that exercise Redis-backed features will require a live Redis connection.

## Project Structure Overview

The codebase is organized in strict layers so that each layer has a single, well-defined responsibility.

`asgi.py` at the root is the uvicorn entrypoint and Click CLI wrapper. It loads environment variables and launches the server. Internally, it imports the `app` object from `app/api/server.py`.

`app/api/server.py` contains the `create_app()` factory. This is where the FastAPI instance is built, middleware is registered (request logging, CORS, and error handling), and the lifespan handler is attached. The lifespan runs Alembic migrations on startup.

`app/api/v1/router.py` assembles all route modules under the `/v1` prefix. Every feature module registers its own `APIRouter` here. This file is the single place where you can see every endpoint group the service exposes.

`app/api/v1/routes/dpdp/` contains the route handlers. These are intentionally thin — they parse the HTTP request, inject dependencies, call a service method, and return a `StandardResponse`. Business logic does not belong here.

`app/services/dpdp/` is where business rules live. Services coordinate across repositories, enforce RBAC permissions, apply encryption, write audit log entries, and raise `HTTPException` for expected failures.

`app/repositories/` contains all SQL query logic. Each repository wraps a set of async SQLAlchemy queries for a particular ORM model. Services call repositories; repositories never call services.

`app/models/orm/` holds the SQLAlchemy ORM models. These are the canonical source of truth for the database schema. Alembic reads these to generate migrations.

`app/schemas/dpdp/` holds Pydantic v2 models for request validation and response serialization. They are the API contract between callers and the service layer.

`app/core/` contains cross-cutting infrastructure: middleware, logging configuration, the standard response factory, RBAC enforcement, and cryptographic utilities.

## Common Issues and Fixes

**Database connection refused on startup.** MySQL is not running or is not reachable at the configured `DB_HOST` and `DB_PORT`. Start MySQL and verify connectivity with `mysql -u root -p` before launching the service.

**Missing environment variables.** If the server exits immediately with a `KeyError` or a `None` value in a critical setting, the most likely cause is that `.env` has not been created. Run `cp local.env .env` and fill in the required values, particularly `JWT_SECRET_KEY`, `DPDP_DEK_HEX`, and `DPDP_HMAC_KEY_HEX`.

**Alembic migration errors.** If `alembic upgrade head` fails with an `OperationalError`, check that the database exists and that `DB_USER` has full DDL privileges on it. If you see a `Can't DROP` error referencing a column or index that does not exist, the migration history in the `alembic_version` table may be out of sync with the actual schema. In development you can drop the database and recreate it, then run migrations fresh.

**`DPDP_DEK_HEX` must be 64 hex characters.** The `get_dek()` utility validates this at startup. Passing a 32-character string (16 bytes) instead of 64 characters (32 bytes) will raise a `ValueError`. Always generate the key with `secrets.token_hex(32)`.
