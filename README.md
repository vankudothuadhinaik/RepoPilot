# RepoPilot

<p align="center">
  <strong>Repository intelligence with evidence you can inspect.</strong><br/>
  Index a local codebase, search its source, trace symbols and imports, and retrieve line-addressable evidence — without letting an automated agent execute repository commands or apply patches.
</p>

<p align="center">
  <a href="https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/codeql.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.11–3.12" src="https://img.shields.io/badge/python-3.11%20%7C%203.12-3776AB.svg">
  <img alt="Local-first" src="https://img.shields.io/badge/storage-local--first-555.svg">
</p>

RepoPilot is a local-first repository investigation tool for developers exploring unfamiliar codebases. It combines incremental indexing, SQLite full-text search, Python symbol extraction, conservative import/include relationships, cited evidence, optional grounded answers, and an optional web dashboard.

> **Project status:** MVP for local development and evaluation. The repository's synthetic benchmark is a repeatable smoke/evaluation aid, not evidence of production retrieval accuracy. See [Evaluation and evidence](#evidence-and-verification).

## What it does

- **Indexes local repositories** with content-hash-based incremental re-indexing.
- **Filters files conservatively**, including common secret paths, generated directories, binaries, symlinks, and files larger than 1 MB.
- **Extracts Python symbols** using the AST, including nested qualified names, signatures, and source ranges.
- **Maps import/include relationships** conservatively across Python, JavaScript/TypeScript, Java/Kotlin, Go, C/C++, Rust, and C#.
- **Searches locally** using SQLite FTS5 with language and path filters.
- **Returns inspectable evidence** with repository paths and line ranges, rather than asking users to trust an uncited summary.
- **Supports optional integrations** for OpenAI-compatible grounded answers, MCP tools, and a React/Vite dashboard.
- **Provides a hardened local container setup** with a shared bearer token supplied at runtime through Doppler.

## Evidence and verification

This section separates automated checks from claims the project does **not** make.

| Evidence source | What it establishes | What it does not establish |
| --- | --- | --- |
| GitHub Actions CI | The configured lint, type-check, test, compile, synthetic evaluation, repository benchmark, frontend build, Docker/Compose validation and container API smoke test, and optional MCP import jobs pass for the tested commit when the workflow is green. | External security certification or production readiness. |
| Synthetic retrieval evaluation | A deterministic 50-query suite exercises lexical path retrieval and negative/abstention cases across three fixture repositories and 15 hand-authored source files. | Performance on representative repositories, semantic retrieval quality, or answer quality from an LLM. |
| Docker smoke test | The built image starts in CI, readiness responds, unauthenticated API access returns 401, and token-authenticated repository listing returns 200; Compose configuration is parsed. | A clean Doppler-driven Windows deployment, persistence/restart verification, or external penetration testing. |
| Authentication checks | API routes under `/api/*` use a shared bearer token; health endpoints are public. | Multi-user identity, roles, per-user authorization, rate limiting, or transport security outside loopback. |

**Latest repository CI:** [view workflow runs](https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/ci.yml). The badge above reflects the workflow status for `main`; check the run page for the exact commit and individual job results.

CI publishes the synthetic retrieval report as `repopilot-retrieval-benchmark-py<version>-<commit-sha>` and a checked-out-repository performance baseline as `repopilot-repository-benchmark-py<version>-<commit-sha>`, separately for Python 3.11 and 3.12, both for 30 days. The report includes Recall@5, Recall@10, MRR@10, abstention accuracy, and per-query expected paths/ranks. Run the same evaluation locally with:

```bash
PYTHONPATH=src python evals/run_eval.py
```

Run a local repository performance baseline with `PYTHONPATH=src python evals/benchmark_repository.py /path/to/repo --output report.json`, or compare multiple authorized local repositories with `PYTHONPATH=src python evals/benchmark_matrix.py /path/to/repo-small /path/to/repo-medium /path/to/repo-large --output benchmark-matrix.json`. See [docs/evaluation.md](docs/evaluation.md) for methodology and limitations. For the optional live-provider evaluation and its strict limitations, see [docs/live-provider-evaluation.md](docs/live-provider-evaluation.md). No benchmark score is claimed here because scores should be read from the report generated for a specific commit.

## Architecture at a glance

```text
Local repository
      |
      v
Safe file discovery and parsing
      |
      +--> file metadata, source ranges, Python symbols
      +--> conservative import/include edges
      |
      v
SQLite + FTS5 index  <---->  repository notes / memories
      |
      +--> CLI
      +--> FastAPI (bearer-protected /api/*)
      +--> optional MCP server
      +--> optional React/Vite dashboard
      |
      v
Search results and line-addressable evidence
      |
      +--> optional OpenAI-compatible grounded answer
```

The application is designed for **inspection, retrieval, and evidence gathering**. It does not execute commands from indexed repositories or apply patches. See [architecture](docs/architecture.md) and the [threat model](docs/threat-model.md).

## Quick start

### Requirements

- Python 3.11 or 3.12 with SQLite FTS5 support.
- Git is optional and used for branch/commit metadata.
- Docker Desktop with Compose for container deployment.
- Doppler CLI for the documented container workflow.
- Node.js 22 LTS (22.12 or newer) and npm for dashboard development.

### Install for local development

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Index and list repositories:

```bash
repopilot index /absolute/path/to/project
repopilot repos
```

The default database is `.repopilot/repopilot.sqlite3`. Set `REP_PILOT_DATA_DIR` to use a different data directory.

Run a local API bound to loopback:

```bash
doppler run -- repopilot serve --host 127.0.0.1 --port 8000
```

Local API base URL: `http://127.0.0.1:8000`.

## Docker Compose

The supported Compose workflow uses Doppler project `repopilot`, config `dev`, to inject the required `REP_PILOT_API_TOKEN` at runtime. Never commit or print the token.

```bash
doppler configure get project config
doppler run -- docker compose up --build -d
doppler run -- docker compose ps
doppler run -- docker compose logs --no-color --tail=50 repopilot
```

- API documentation: [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)
- Liveness: [http://127.0.0.1:8010/health/live](http://127.0.0.1:8010/health/live)
- Readiness: [http://127.0.0.1:8010/health/ready](http://127.0.0.1:8010/health/ready)

Compose publishes container port `8000` to host loopback port `8010`. The configured service runs as non-root, drops Linux capabilities, enables `no-new-privileges`, uses a read-only root filesystem with `/tmp` as tmpfs, and stores persistent data in the `repopilot_data` named volume.

The default Compose file does not mount arbitrary host source directories into the container. A path submitted to the Docker API must already be visible inside the container (for example `/app`); use the local Python API when indexing a Windows or macOS host path, or add an explicitly reviewed read-only bind mount for a controlled deployment.

If port 8010 is occupied, change the host side only (for example `127.0.0.1:8011:8000`) and update the dashboard proxy/URLs together. Avoid stopping unrelated containers or deleting the named volume.

### Authentication

Every `/api/*` route requires:

```http
Authorization: Bearer <REP_PILOT_API_TOKEN>
```

Missing or invalid credentials return `401`. `/health/live` and `/health/ready` are public for monitoring. This is a single shared local token, **not** a multi-user identity or role system.

Example request without printing the token:

**macOS/Linux**

```bash
API_TOKEN="$(doppler secrets get REP_PILOT_API_TOKEN --plain)"
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8010/api/repos
unset API_TOKEN
```

**Windows PowerShell**

```powershell
$apiToken = doppler secrets get REP_PILOT_API_TOKEN --plain
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/repos -Headers @{ Authorization = "Bearer $apiToken" }
Remove-Variable apiToken
```

Avoid shell tracing or commands that echo environment values. Compose validation without Doppler is expected to fail safely when the required token interpolation is missing.

## Dashboard

The dashboard is a development frontend; Compose does not serve it. From `apps/web`:

```bash
npm ci
npm run dev
```

Open the URL Vite prints. Enter the token in the **Local API token** password field; it is provided at runtime and is not hard-coded in the frontend.

## API example

The following uses the Docker API base URL and the Doppler-managed token. The request body is illustrative; replace the path with a repository accessible to the process.

```bash
API_TOKEN="$(doppler secrets get REP_PILOT_API_TOKEN --plain)"

curl -H "Authorization: Bearer $API_TOKEN" \
  http://127.0.0.1:8010/api/repos

curl -X POST http://127.0.0.1:8010/api/repos \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"/absolute/path/to/project"}'

unset API_TOKEN
```

See [docs/api.md](docs/api.md) or the interactive [OpenAPI docs](http://127.0.0.1:8010/docs) for the full route reference.

## Development checks

Run these from the repository root:

```bash
python -m pytest
python -m ruff check .
python -m mypy src/repopilot
python -m compileall -q src
PYTHONPATH=src python evals/run_eval.py
python evals/run_ground_truth.py --root .
```

Frontend checks:

```bash
cd apps/web
npm ci
npm audit --audit-level=moderate
npm run build
```

The CI workflow runs the configured checks on Python 3.11 and 3.12, builds the frontend and Docker image, and verifies that the optional MCP server imports. Check the live workflow for the exact run result rather than relying on a README statement.

The ground-truth evaluator is a separate, small source-level check for Recall@5, MRR@5, symbol-range accuracy, citation line correctness, and unsupported-query abstention. See [docs/evaluation.md](docs/evaluation.md) and [docs/validation_report.md](docs/validation_report.md) for definitions, commands, and the latest recorded run.

## Current limitations

RepoPilot is intentionally scoped as an MVP. The following are **not implemented**:

- Semantic embeddings or reranking.
- Complete compiler-level call graphs or language-server-grade parsing.
- Background jobs and distributed indexing.
- Cloud repository import or patch application.
- Repository command execution.
- Multi-user tenancy, production identity/authorization, and role-based access.
- Built-in rate limiting or a hosted production security posture.

Repository content must be treated as untrusted input. Secret-path exclusions reduce exposure but cannot detect every credential. The API is intended for loopback use; bearer authentication does not replace TLS, rate limiting, identity, roles, or an environment-specific security review for hosted use.

## Documentation

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, data flow, and design boundaries |
| [API reference](docs/api.md) | Routes, request/response schemas, authentication |
| [Threat model](docs/threat-model.md) | Assets, trust boundaries, threats, and residual risk |
| [Security policy](SECURITY.md) | Vulnerability reporting and security expectations |
| [Evaluation methodology](docs/evaluation.md) | Synthetic benchmark scope, metrics, and next steps |
| [MCP setup](docs/mcp-setup.md) | Optional MCP server configuration |
| [LLM providers](docs/llm-providers.md) | Optional grounded-answer provider configuration |
| [Quality tooling](docs/quality-tools.md) | Development quality and CI tools |
| [Troubleshooting](docs/troubleshooting.md) | Common local runtime issues |
| [Contributing](CONTRIBUTING.md) | Contribution workflow |

## License

MIT — see [LICENSE](LICENSE).


### Multi-repository evaluation status

The offline multi-repository evaluation uses 41 maintainer-authored cases (31 positive, 10 unsupported) across RepoPilot plus three recorded external source snapshots. Its dataset records provenance and commit IDs; the evaluator materializes the recorded RepoPilot Git revision by default and fails if it is unavailable. Pass `--use-checkout` only to explicitly evaluate proposed worktree changes. CI publishes per-case results as an artifact. Expected source ranges are checked automatically, but independent second-person review remains pending. Automated retrieval and citation checks do not establish semantic claim entailment; live provider evaluation remains opt-in and depends on available provider credits. See [the evaluation audit](docs/evaluation_audit.md) for the case-by-case review and provenance limits.
