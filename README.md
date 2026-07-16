# Consent Management Backend

A FastAPI microservice for managing citizen consent in compliance with India's Digital Personal Data Protection (DPDP) Act 2023. It handles consent forms, consent lifecycle, audit trails, data subject rights, and analytics for organisations that need to collect and prove lawful consent from their users.

The service is designed to be called by other microservices in your platform. Your auth service or mobile backend sends consent events using an organisation-scoped API key, and this service stores, validates, and receipts them in a tamper-evident way.

## Documentation

All documentation lives in the [docs](docs/) directory.

[Setup Guide](docs/SETUP.md) covers prerequisites, environment configuration, running locally, and Docker.

[API Reference](docs/API.md) lists every endpoint with request and response examples.

[Codebase Guide](docs/CODEBASE.md) explains the architecture, layers, and patterns used throughout the project.

[Database Reference](docs/DATABASE.md) documents the schema, migrations, and encryption approach.

[API Flow Guide](docs/API_FLOW_GUIDE.md) walks through complete end-to-end workflows.

[Deployment Guide](docs/DEPLOYMENT.md) covers production setup, Nginx, systemd, and the security checklist.

The [features](docs/features/) directory has one document per service module explaining its endpoints, data model, and implementation details.

## Quick Start

```bash
git clone <repo-url>
cd consent-management
poetry env use python3.12
poetry install --no-root
cp local.env .env   # then fill in your database and secret values
alembic upgrade head
python asgi.py --env local
```

The API documentation is available at http://localhost:9000/docs once the server is running.

## Tech Stack

Python 3.12, FastAPI 0.125, SQLAlchemy 2 (async), MySQL 8, Redis 7, Alembic, Poetry.
