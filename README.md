# RepoPilot

RepoPilot is a local-first repository intelligence tool. It indexes a codebase, searches its source with SQLite FTS5, discovers Python symbols and imports, and stores engineering notes with file evidence.

It is designed for developers investigating an unfamiliar repository without granting an automated agent permission to execute commands or apply patches.

## Features

- Register and re-index local repositories.
- Exclude common secret-bearing paths, generated directories, binaries, symlinks, and files larger than 1 MB.
- Extract Python classes and functions with the standard-library AST parser.
- Extract static Python import relationships.
- Search indexed text with SQLite FTS5.
- Retrieve file evidence, snippets, symbols, import graphs, repository metadata, and engineering memories.
- Provide an optional MCP server for repository listing, search, symbol lookup, overviews, and memory retrieval.
- Offer a small React dashboard with a local API-token field.
- Run as a hardened, loopback-only Docker Compose service.

## Current status and limitations

This is an early MVP. Implemented behavior is covered by the test suite, but it is not a production-hosted service.

Not implemented:

- Semantic embeddings, reranking, or LLM-generated explanations.
- Complete symbol/call-graph analysis for languages other than Python.
- Incremental per-file indexing or background indexing jobs.
- Multi-user tenancy, cloud repository import, patch application, or shell-command execution.
- Rate limiting, a production identity system, or a large retrieval benchmark.

The `/api/*` routes require a bearer token. `/health/live` and `/health/ready` are intentionally public for local monitoring.

## Architecture

RepoPilot is a local modular monolith:

1. The CLI and FastAPI application call the repository indexer.
2. Safe file discovery filters untrusted repository content before reading it.
3. Python AST and import extraction produce searchable records.
4. SQLite and FTS5 store repository metadata, text, symbols, graph edges, and memories.
5. The API, dashboard, and optional MCP server read from that local store.

The Docker image listens on container port `8000`. Compose publishes it only on host loopback port `8010`.

See [`docs/architecture.md`](docs/architecture.md) for the component view.

## Prerequisites

- Python 3.11 or 3.12.
- SQLite with FTS5, included in most standard Python distributions.
- Git is optional and is used for branch/commit metadata when available.
- Docker Desktop and Compose for the container deployment.
- Doppler CLI for the supported authenticated Docker workflow.
- Node.js and npm only when running the dashboard.

The repository is configured for Doppler project `repopilot`, config `dev`. Confirm the local selection with:

```bash
doppler configure get project config
```

Do not print, commit, or place `REP_PILOT_API_TOKEN` in a tracked file or a secret-bearing `.env` file.

## Local Python development

Create an environment and install the project with development tools.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The CLI uses `.repopilot/repopilot.sqlite3` by default. Set `REP_PILOT_DATA_DIR` to use another data directory.

Index and inspect a repository:

```bash
repopilot index /absolute/path/to/project
repopilot repos
```

Run the local API on its default loopback URL. Because `/api/*` is authenticated, start it through the configured Doppler context:

```bash
doppler run -- repopilot serve --host 127.0.0.1 --port 8000
```

The local API is then available at `http://127.0.0.1:8000`; this is different from the Docker host URL below.

## Docker Compose deployment

The supported deployment keeps the container on port `8000` and publishes it as `127.0.0.1:8010`. Doppler supplies the token to Compose, and Compose refuses to render or start the service if `REP_PILOT_API_TOKEN` is unset or empty.

Run from the repository root:

```bash
doppler configure get project config
doppler run -- docker compose up --build -d
doppler run -- docker compose ps
doppler run -- docker compose logs --no-color --tail=50 repopilot
```

Public health checks:

```bash
curl http://127.0.0.1:8010/health/live
curl http://127.0.0.1:8010/health/ready
```

Open the API documentation at [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs). The service binds to loopback, drops all Linux capabilities, enables `no-new-privileges`, uses a read-only root filesystem with `/tmp` as tmpfs, runs as a non-root user, and persists its SQLite database in the `repopilot_data` named volume.

If host port `8010` is occupied, change only the host side of the mapping, for example `127.0.0.1:8011:8000`, and update the dashboard proxy and URLs together. Do not stop unrelated containers or expose this unauthenticated-to-the-network service publicly.

## Authentication and safe token handling

`REP_PILOT_API_TOKEN` is required for every `/api/*` route. Missing, malformed, or incorrect bearer credentials return `401`. The health endpoints remain public so local monitoring can determine whether the process and storage are available.

Use the token in memory; do not echo it or put it in source control.

macOS/Linux:

```bash
API_TOKEN="$(doppler secrets get REP_PILOT_API_TOKEN --plain)"
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8010/api/repos
unset API_TOKEN
```

Windows PowerShell:

```powershell
$apiToken = doppler secrets get REP_PILOT_API_TOKEN --plain
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/repos -Headers @{ Authorization = "Bearer $apiToken" }
Remove-Variable apiToken
```

Do not use `docker compose config` without the Doppler environment because the required interpolation will fail. Avoid commands or shell tracing that could print environment values.

## Dashboard

The dashboard is a development frontend; Compose does not serve it. Its Vite proxy points to `http://127.0.0.1:8010`, and the UI sends the token entered in its password field with API requests.

Install and run it from `apps/web`:

```bash
npm install
npm run dev
```

Open the URL printed by Vite, enter the value of `REP_PILOT_API_TOKEN` from Doppler into the **Local API token** field, and use the dashboard. The token is held by the browser page for requests and is not hard-coded into the frontend.

## API usage

The Docker API base URL is `http://127.0.0.1:8010`; use port `8000` for a local `repopilot serve` process. Health endpoints do not require authentication. All `/api/*` examples require the bearer header:

```bash
API_TOKEN="$(doppler secrets get REP_PILOT_API_TOKEN --plain)"

curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8010/api/repos

curl -X POST http://127.0.0.1:8010/api/repos \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"/absolute/path/to/project"}'

curl -X POST http://127.0.0.1:8010/api/repos/REPOSITORY_ID/search \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"authentication","limit":8}'

unset API_TOKEN
```

Available route groups include repository registration and metadata, indexing, search, evidence retrieval, symbols, import graphs, files, and memory CRUD. See [`docs/api.md`](docs/api.md) and the interactive `/docs` page for the complete list.

## Tests, checks, and CI

Run the local Python checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python -m compileall -q src
python evals/run_eval.py
```

Run the frontend check:

```bash
cd apps/web
npm install
npm run build
```

The smoke evaluation is a deterministic wiring check, not an accuracy benchmark. GitHub Actions runs Ruff, pytest, and Python compilation on Python 3.11 and 3.12. CodeQL scans Python, and Dependabot monitors pip and GitHub Actions dependencies.

## Security model

Repository content is untrusted input. RepoPilot skips common secret paths, symlinks, generated directories, binaries, and oversized files; it does not claim to detect every credential. The application does not execute repository commands or apply patches.

The API is intended for local loopback use. Bearer authentication protects `/api/*`, but this is not a full identity, tenancy, rate-limiting, or production authorization system. Review [`SECURITY.md`](SECURITY.md) and [`docs/threat-model.md`](docs/threat-model.md) before handling sensitive repositories.

## Documentation and contribution

- [`docs/architecture.md`](docs/architecture.md) — components and boundaries.
- [`docs/api.md`](docs/api.md) — route reference.
- [`docs/mcp-setup.md`](docs/mcp-setup.md) — optional MCP server.
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation scope and limitations.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — deployment and runtime troubleshooting.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow.
- [`SECURITY.md`](SECURITY.md) — security policy.

Add tests for behavior changes, run the relevant checks, and never commit credentials, private repository content, production data, `.env` files, or local `.repopilot/` databases.

## License

RepoPilot is released under the MIT License. See [`LICENSE`](LICENSE).
