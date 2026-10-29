# RepoPilot

**Evidence-grounded repository intelligence for developers.** Index a local codebase, search its source, discover Python symbols and imports, and preserve engineering notes—with file evidence rather than unsupported claims.

> Status: early MVP starter. This repository is prepared for GitHub connection, but has not yet been run in your environment. See the feature boundaries below; do not treat planned capabilities as implemented.

## Why RepoPilot?

RepoPilot aims to help developers understand unfamiliar repositories, find relevant code, inspect dependencies, remember engineering decisions, and investigate bugs. Its first release prioritizes a safe, testable local core over autonomous code editing.

## Implemented in this starter

- Local repository registration and re-indexing.
- File filtering, common secret-file exclusions, symlink skipping, and file-size limits.
- Python function/class discovery using the standard-library AST parser.
- Python import relationship extraction.
- SQLite metadata and FTS5 full-text search.
- Search, symbols, graph, file evidence, and memory CRUD API endpoints.
- Evidence retrieval endpoint that explicitly does **not** pretend to generate a semantic LLM answer.
- Optional MCP tools for repository listing, code search, symbol lookup, overview, and memory retrieval.
- Unit/API/security regression tests, GitHub Actions CI, CodeQL workflow, Dependabot, Docker, and Compose.
- Architecture, threat model, API, MCP, evaluation, and troubleshooting docs.

## Not implemented yet

- Semantic embeddings or reranking.
- LLM-generated explanations and provider adapters.
- Complete Java/C++/TypeScript symbol and call-graph analysis.
- Incremental per-file re-indexing (the current implementation replaces one repository's index).
- Background indexing jobs.
- Web UI beyond the starter directory.
- Authentication, multi-user tenancy, cloud repository import, approved patch application, and isolated command execution.
- A meaningful 50+ question benchmark or production security certification.

These are explicit follow-up milestones, not completed claims.

## Requirements

- Python 3.11 or 3.12
- Git optional for branch/commit metadata
- SQLite with FTS5 (included in most standard Python distributions)

## Quick start

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Index a repository:

```bash
repopilot index /absolute/path/to/your/project
repopilot repos
repopilot serve
```

Open `http://127.0.0.1:8000/docs`, register a repository with `POST /api/repos`, and use the returned repository ID to search or list symbols. The database defaults to `.repopilot/repopilot.sqlite3`; set `REP_PILOT_DATA_DIR` to change it.

### API example

```bash
curl -X POST http://127.0.0.1:8000/api/repos \
  -H "Content-Type: application/json" \
  -d '{"path":"/absolute/path/to/your/project"}'
```

Then:

```bash
curl -X POST http://127.0.0.1:8000/api/repos/REPOSITORY_ID/search \
  -H "Content-Type: application/json" \
  -d '{"question":"authentication","limit":8}'
```

## Tests and checks

```bash
ruff check .
pytest
python -m compileall -q src
python evals/run_eval.py
```

The smoke evaluation is only a wiring check; it is not a benchmark accuracy result. CI runs lint, tests, and compilation on Python 3.11 and 3.12.

## Docker

```bash
docker compose up --build
```

The Compose service binds to loopback, drops Linux capabilities, uses a read-only root filesystem, and persists its database in a named volume. Do not expose the unauthenticated API to the public internet.

## Optional MCP

```bash
pip install -e ".[mcp]"
python -m repopilot.mcp_server
```

See [`docs/mcp-setup.md`](docs/mcp-setup.md).

## Security and privacy

Read [`SECURITY.md`](SECURITY.md) and [`docs/threat-model.md`](docs/threat-model.md). Repository content is untrusted input. This MVP does not execute shell commands or apply patches. The API has no authentication; use loopback only. Common secret-bearing paths are excluded, but users must review exclusions before indexing sensitive repositories.

## Architecture

See [`docs/architecture.md`](docs/architecture.md), [`docs/api.md`](docs/api.md), and [`docs/evaluation.md`](docs/evaluation.md).

## Roadmap

1. Add robust file-level incremental indexing and job status.
2. Add language parsers and tested symbol/call relationships.
3. Add hybrid retrieval and an optional provider interface with evidence validation.
4. Add a polished UI, session handling, and explainable investigation workflow.
5. Add an evaluated memory-freshness model.
6. Harden authentication, tenancy, and isolated approved actions only if hosted execution is required.
7. Publish a reviewed benchmark and release notes.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Never commit `.env` files, API keys, private repository source, or local index databases.

## License

MIT. See [`LICENSE`](LICENSE).
