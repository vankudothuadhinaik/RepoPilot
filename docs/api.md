# API quick reference

Base URL: `http://127.0.0.1:8010` for Docker Compose. A local `repopilot serve` process defaults to `http://127.0.0.1:8000`.

- `GET /health/live` — liveness.
- `GET /health/ready` — storage readiness.
- `GET /api/*` routes require `Authorization: Bearer <REP_PILOT_API_TOKEN>`; missing or invalid tokens return `401`.
- `GET /api/repos` — list indexed repositories.
- `POST /api/repos` — JSON `{"path": "/absolute/path/to/repository"}`.
- `GET /api/repos/{id}` — repository metadata and coverage.
- `POST /api/repos/{id}/index` — re-index the registered local path.
- `POST /api/repos/{id}/search` — JSON `{"question":"auth","limit":8}`.
- `POST /api/repos/{id}/ask` — evidence retrieval baseline; does not generate an LLM answer.
- `GET /api/repos/{id}/symbols?q=Service` — discovered symbols.
- `GET /api/repos/{id}/graph` — extracted import relationships.
- `GET /api/repos/{id}/files/{path}` — indexed file content.
- `GET /api/repos/{id}/memories` — engineering memories.
- `POST /api/repos/{id}/memories` — create a proposed/verified note.
- `PATCH /api/memories/{id}` — update summary or status.
- `DELETE /api/memories/{id}` — delete a memory.
- `DELETE /api/repos/{id}` — remove repository index records.

Open `/docs` for the interactive OpenAPI schema.

The Docker deployment obtains `REP_PILOT_API_TOKEN` from Doppler. Send it as `Authorization: Bearer <token>` on every `/api/*` request. `/health/live` and `/health/ready` are public. Missing or invalid API credentials return `401`.
