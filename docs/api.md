# API quick reference

Base URL: `http://127.0.0.1:8010` for Docker Compose. A local `repopilot serve` process defaults to `http://127.0.0.1:8000`.

- `GET /health/live` — liveness.
- `GET /health/ready` — storage readiness.
- `GET /api/repos` — list indexed repositories.
- `POST /api/repos` — JSON `{"path": "/absolute/path/to/repository"}`.
- `GET /api/repos/{id}` — repository metadata and coverage.
- `POST /api/repos/{id}/index` — re-index the registered local path; returns `index_delta` counts for added, updated, removed, unchanged, and scanned files.
- `POST /api/repos/{id}/search` — JSON `{"question":"auth","limit":8}`; optional `language` and `path_prefix` filters are applied before ranking/limiting. Directory prefixes match the directory itself and descendants, not similarly named sibling paths.
- `POST /api/repos/{id}/ask` — returns source path, bounded line range, snippet, SHA-256, and indexed commit; optional OpenAI-compatible generation is enabled with provider environment variables and falls back to retrieval-only mode when provider output fails validation. Citation paths are validated, but generated prose is not formally claim-verified.
- `GET /api/repos/{id}/symbols?q=Service` — discovered symbols.
- `GET /api/repos/{id}/graph` — extracted import relationships.
- `GET /api/repos/{id}/files/{path}` — indexed file content.
- `GET /api/repos/{id}/memories` — engineering memories.
- `POST /api/repos/{id}/memories` — create a note with status `proposed`, `verified`, `superseded`, or `rejected` (default `proposed`).
- `PATCH /api/memories/{id}` — update summary or status; invalid statuses return `400`.
- `DELETE /api/memories/{id}` — delete a memory.
- `DELETE /api/repos/{id}` — remove repository index records.

Docker obtains `REP_PILOT_API_TOKEN` from Doppler and requires `Authorization: Bearer <token>` on every `/api/*` request. Missing or invalid credentials return `401`. Health endpoints remain public. All `/api/*` routes, including mutations and memory/repository deletion, require the bearer token. Validation errors use FastAPI's `422` response; invalid repository paths or memory status values return controlled `400` responses. Open `/docs` for the interactive OpenAPI schema.

For Docker Compose, repository paths are resolved inside the container. The default Compose file persists `/data` but does not expose arbitrary host source directories; use the local API for host paths or provide a deliberate read-only bind mount.
