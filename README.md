# RepoPilot

RepoPilot is a local-first repository intelligence tool. It indexes a codebase, searches source with SQLite FTS5, discovers symbols and import relationships, retrieves line-addressable evidence, and stores engineering notes.

It is intended for developers investigating unfamiliar repositories without allowing an automated agent to execute repository commands or apply patches.

## Current implementation

- Local repository registration and content-hash-based incremental re-indexing.
- Secret-path, generated-directory, binary, symlink, and 1 MB file-size filtering.
- Python AST symbols with nested qualified names, signatures, and source ranges.
- Conservative import/include extraction for Python, JavaScript/TypeScript, Java/Kotlin, Go, C/C++, Rust, and C#.
- SQLite metadata, FTS5 search, language/path filters, symbols, graphs, files, memories, and evidence citations.
- Optional OpenAI-compatible grounded answers with retrieval-only fallback.
- Optional MCP tools and a React/Vite dashboard.
- Hardened Docker Compose deployment with Doppler-supplied API authentication.

This remains an MVP. Semantic embeddings/reranking, complete compiler-level call graphs, background jobs, multi-user tenancy, cloud import, patch application, command execution, rate limiting, and production identity/authorization are not implemented. The synthetic retrieval benchmark is not a real-world accuracy claim.

## Architecture

The CLI and FastAPI application call the safe indexer. Parsed text, symbols, import edges, repository metadata, and memories are stored in SQLite/FTS5. The dashboard and optional MCP server use the same local store. `/ask` returns cited evidence and can optionally call an OpenAI-compatible provider; it does not claim unsupported answers.

The image listens on container port `8000`. Compose publishes it only on host loopback port `8010`.

See [`docs/architecture.md`](docs/architecture.md).

## Prerequisites

- Python 3.11 or 3.12 with SQLite FTS5.
- Git is optional for branch/commit metadata.
- Docker Desktop and Compose for container deployment.
- Doppler CLI for the supported deployment workflow.
- Node.js and npm for the dashboard.

The configured secret source is Doppler project `repopilot`, config `dev`:

```bash
doppler configure get project config
```

Never print, commit, or place `REP_PILOT_API_TOKEN` in a tracked file or secret-bearing `.env` file.

## Local Python development

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

The default database is `.repopilot/repopilot.sqlite3`; set `REP_PILOT_DATA_DIR` to change it. Index a repository with:

```bash
repopilot index /absolute/path/to/project
repopilot repos
```

Run the local API on loopback port 8000 through Doppler:

```bash
doppler run -- repopilot serve --host 127.0.0.1 --port 8000
```

The local API is at `http://127.0.0.1:8000`. Docker uses host port 8010 instead.

## Docker Compose deployment

Compose requires a non-empty `REP_PILOT_API_TOKEN` and passes it from the Doppler process into the container. Run from the repository root:

```bash
doppler configure get project config
doppler run -- docker compose up --build -d
doppler run -- docker compose ps
doppler run -- docker compose logs --no-color --tail=50 repopilot
```

The service URL is [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs). Health checks are public:

```bash
curl http://127.0.0.1:8010/health/live
curl http://127.0.0.1:8010/health/ready
```

The service binds to loopback, runs as a non-root user, drops all capabilities, enables `no-new-privileges`, uses a read-only root filesystem with `/tmp` as tmpfs, and persists data in the `repopilot_data` named volume. If 8010 is occupied, change only the host side, for example `127.0.0.1:8011:8000`, and update the dashboard proxy and URLs together. Do not stop unrelated containers or delete the volume.

## Authentication and token handling

Every `/api/*` route requires `Authorization: Bearer <REP_PILOT_API_TOKEN>`. Missing or invalid credentials return `401`; `/health/live` and `/health/ready` remain public for monitoring. This is one shared local token, not a user identity or role system.

Use the token in memory without echoing it.

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

Do not run shell tracing or commands that print environment values. Compose validation without Doppler is expected to fail safely because the required interpolation is missing.

## Dashboard

The dashboard is a development frontend; Compose does not serve it. Its Vite proxy targets `http://127.0.0.1:8010`. From `apps/web`:

```bash
npm ci
npm run dev
```

Open the URL printed by Vite, enter the Doppler token in the **Local API token** password field, and then register/search repositories or retrieve evidence. The token is supplied by the user at runtime and is not hard-coded into the frontend.

## API usage

The Docker API base URL is `http://127.0.0.1:8010`; use port 8000 for a local server. All API examples need the bearer header:

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

See [`docs/api.md`](docs/api.md) for the complete route reference and interactive `/docs` schema.

## Checks and CI

Python checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy src/repopilot
python -m compileall -q src
PYTHONPATH=src python evals/run_eval.py
```

Frontend check:

```bash
cd apps/web
npm ci
npm audit --audit-level=moderate
npm run build
```

CI runs Ruff, Mypy, coverage-enabled pytest, compilation, the 50-query synthetic retrieval evaluation, frontend build, Docker image build, and optional MCP import checks on supported workflows. It publishes the retrieval report as a commit-specific artifact. CodeQL and Dependabot are also configured.

## Security and documentation

Repository content is untrusted input. RepoPilot skips common secret paths but cannot detect every credential. It does not execute repository commands or apply patches. The API is for loopback use; bearer authentication does not replace TLS, rate limiting, identity, roles, or a security review for hosted deployment.

- [`SECURITY.md`](SECURITY.md) — security policy.
- [`docs/threat-model.md`](docs/threat-model.md) — assets, trust boundaries, and residual risk.
- [`docs/architecture.md`](docs/architecture.md) — components and limits.
- [`docs/api.md`](docs/api.md) — API routes and authentication.
- [`docs/mcp-setup.md`](docs/mcp-setup.md) — optional MCP server.
- [`docs/llm-providers.md`](docs/llm-providers.md) — optional grounded answer provider.
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation scope.
- [`docs/quality-tools.md`](docs/quality-tools.md) — quality tooling.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — runtime troubleshooting.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow.

Never commit credentials, private repository content, production data, `.env` files, or local `.repopilot/` databases.

## License

RepoPilot is released under the MIT License. See [`LICENSE`](LICENSE).
