# RepoPilot

**Evidence-grounded repository intelligence for developers.** Index a local codebase, search its source, discover Python symbols and imports, and preserve engineering notes—with file evidence rather than unsupported claims.

Status: **local-first MVP in active development**. Backend tests, retrieval smoke evaluation, frontend production build, optional MCP import, and Docker image build are checked in CI. Run the Windows/local setup below to verify it in your own environment.

## Why RepoPilot?

RepoPilot aims to help developers understand unfamiliar repositories, find relevant code, inspect dependencies, remember engineering decisions, and investigate bugs. Its first release prioritizes a safe, testable local core over autonomous code editing.

## Implemented in the MVP

- Local repository registration and content-hash-based incremental re-indexing, with per-run added/updated/removed/unchanged counts in the API and dashboard.
- File filtering, common secret-file exclusions, symlink skipping, and file-size limits.
- Python function/class discovery using the standard-library AST parser, including nested qualified names, async functions, signatures, and source line ranges.
- Static import/include edges for Python, JavaScript/TypeScript, Java/Kotlin, Go, C/C++, Rust, and C# (heuristic syntax extraction; not a complete compiler-level dependency graph).
- SQLite metadata and FTS5 full-text search.
- Search, symbols, graph, file evidence, and memory CRUD API endpoints.
- Evidence retrieval endpoint with line-numbered snippets, source hashes, and indexed commit metadata.
- Optional OpenAI-compatible answers with citations validated against retrieved source paths; falls back to retrieval-only when unconfigured or provider output fails validation.
- Optional MCP tools for repository listing, code search, symbol lookup, overview, and memory retrieval.
- Unit/API/security regression tests, GitHub Actions CI, Dependabot, Docker, and Compose. CodeQL analysis runs in CI, but results are not uploaded as code-scanning alerts because GitHub code scanning is not enabled for this private repository.
- Architecture, threat model, API, MCP, evaluation, and troubleshooting docs.

## Evaluation

`python evals/run_eval.py` runs a small smoke test and a deterministic 50-query synthetic retrieval benchmark across three fixture repositories. CI publishes `retrieval_benchmark_results.json` as a commit-specific artifact. The benchmark reports Recall@5, Recall@10, MRR@10, and negative-query abstention accuracy. It validates retrieval wiring against controlled synthetic source files; it is **not** a real-world accuracy or semantic-answer-quality claim.

## Not implemented yet

- Semantic embeddings or reranking.
- Additional LLM provider adapters beyond the OpenAI-compatible chat-completions interface.
- Complete Java/C++/TypeScript symbol and call-graph analysis.
- Filesystem walking and hashing are still full-tree on reindex; unchanged file parsing and SQLite/FTS writes are skipped, with changed/deleted paths updated incrementally.
- Background indexing jobs.
- Multi-user tenancy, cloud repository import, approved patch application, and isolated command execution. Optional bearer-token protection is available for the HTTP API; it is not a full identity or role system.
- A real-world, independently reviewed retrieval benchmark or production security certification.

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

Open `http://127.0.0.1:8000/docs`, register a repository with `POST /api/repos`, and use the returned repository ID to search or list symbols. The database defaults to `.repopilot/repopilot.sqlite3`; set `REP_PILOT_DATA_DIR` to change it. The API is intended for loopback use by default. To protect API routes with a bearer token, set `REP_PILOT_API_TOKEN` to a long random secret; then send `Authorization: Bearer YOUR_TOKEN` on `/api/*` requests. The CLI refuses non-loopback binds unless this token is configured. This is a single shared token, not user authentication or multi-tenant authorization.

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

The smoke evaluation is only a wiring check; it is not a benchmark accuracy result. CI runs lint, tests, compilation, and retrieval smoke evaluation on Python 3.11 and 3.12; it also builds the React UI, builds the Docker image, and checks the optional MCP server import.

## Web dashboard

The React dashboard lives in `apps/web`. Start the API in one terminal with `repopilot serve`, then run the UI in another:

```bash
cd apps/web
npm install
npm run dev
```

Open the local Vite URL printed by the command. The dashboard can register local repositories, search indexed text, and retrieve line-addressable evidence citations. The Vite dev server proxies API and health requests to `127.0.0.1:8000`.

## Docker

The container requires an API bearer token because it listens on the container network interface.

PowerShell:

```powershell
$env:REP_PILOT_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up --build
```

macOS/Linux:

```bash
export REP_PILOT_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose up --build
```

The Compose service binds to host loopback, drops Linux capabilities, uses a read-only root filesystem, and persists its database in a named volume. Send `Authorization: Bearer YOUR_TOKEN` on `/api/*` requests. Store production tokens in a secret manager such as Doppler; never commit the token to source control.

## Optional MCP

```bash
pip install -e ".[mcp]"
python -m repopilot.mcp_server
```

See [`docs/mcp-setup.md`](docs/mcp-setup.md) and [`docs/llm-providers.md`](docs/llm-providers.md).

## Security and privacy

Read [`SECURITY.md`](SECURITY.md) and [`docs/threat-model.md`](docs/threat-model.md). Repository content is untrusted input. This MVP does not execute shell commands or apply patches. The API supports optional bearer-token protection; the container requires a token and Compose binds to loopback. This shared token is not a substitute for identity, roles, TLS, or a security review. Common secret-bearing paths are excluded, but users must review exclusions before indexing sensitive repositories.

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
