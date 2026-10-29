[![CI](https://github.com/vankudothuadhinaik/DataPulse-Analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/vankudothuadhinaik/DataPulse-Analytics/actions/workflows/ci.yml)

# DataPulse Analytics

A portfolio-scale event analytics demo with a FastAPI backend, SQLAlchemy persistence, PostgreSQL via Docker Compose, and a React/TypeScript dashboard.

## Implemented API

- `GET /health` — lightweight liveness response.
- `GET /health/ready` — checks that the database can answer a query; returns HTTP 503 when the database is unavailable.
- `POST /events` — validates and persists an event record; rejects blank/oversized identifiers, unknown fields, negative values, and non-finite event values.
- `GET /analytics/metrics` — aggregates event, distinct-user, distinct-session, and event-value totals.
- `GET /analytics/top-events` — returns the ten most common event names with deterministic tie ordering.
- Configurable CORS for the local dashboard, controlled by `CORS_ALLOWED_ORIGINS`.

Interactive API documentation is available at `/docs` when the backend is running.

## Stack

- Python, FastAPI, Pydantic, SQLAlchemy
- PostgreSQL (with psycopg)
- React, TypeScript, Vite, and Recharts
- Docker Compose for local services
- Pytest and GitHub Actions for backend endpoint and validation tests

Redis is included in the local Compose environment and configured through `REDIS_URL`, but the current API code does not yet use Redis for caching, queues, or analytics. The API supports a shared API key for event ingestion and analytics routes; this is a simple service-level gate, not user identity, role-based authorization, or a full account system. Versioned Alembic migrations are provided for the `events` schema; production must apply them as a release step before starting the API, and the API no longer runs `create_all` when `ENVIRONMENT=production` or `prod`. Ingestion rate limiting and full user authorization remain future work. The readiness endpoint is a dependency check, not a deployment-readiness guarantee.

## Run locally

Copy the environment template and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

Open the dashboard at http://localhost:5173 and the API docs at http://localhost:8000/docs.

For a non-default API address in a Vite frontend build, set `VITE_API_BASE_URL` (for example, `https://api.example.com`). The local default is `http://localhost:8000`.

Generate sample records with:

```bash
docker compose exec api python -m app.seed
```

Run the backend tests:

```bash
pip install -r backend/requirements.txt
pytest backend/tests
```

The tests use an isolated in-memory SQLite database and cover health, event ingestion, metric aggregation, top-event ordering, payload validation, and local CORS preflight behavior.

## Configuration and safety

Review `.env.example` before deployment. The credentials in Compose defaults are for local development only; replace them for any shared or hosted environment and keep real secrets out of Git.

For a hosted backend, configure `DATAPULSE_API_KEY` as a secret and set `ENVIRONMENT=production`. Before starting the API on a new or upgraded database, run `cd backend && alembic upgrade head` as a controlled release step; CI checks the initial migration against PostgreSQL and runs `alembic check`. Send the configured key in the `X-API-Key` header for `POST /events`, `GET /analytics/metrics`, and `GET /analytics/top-events`. In production mode, these routes return HTTP 503 if the key is not configured and HTTP 401 if the supplied key is missing or incorrect. Health endpoints remain unauthenticated for orchestration. Use HTTPS and a secret manager; do not put the key in source control or a public frontend bundle.

## Scope

This is a learning/demo project, not a production analytics service. Database migrations, authentication/authorization, ingestion rate limits, operational observability, and broader frontend workflows remain future work.
