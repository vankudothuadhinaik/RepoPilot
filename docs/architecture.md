# Architecture

RepoPilot starts as a local-first modular monolith.

```mermaid
flowchart TD
    CLI[CLI] --> Core[Indexer and API]
    UI[Web UI - planned starter] --> Core
    MCP[MCP server - optional extra] --> Store[(SQLite + FTS5)]
    Core --> Indexer[Safe file discovery and Python AST parser]
    Indexer --> Store
    Core --> Search[Keyword / FTS retrieval]
    Search --> Evidence[Path + snippet + commit evidence]
    Core --> Memory[Engineering memory]
    Memory --> Store
```

## Current implementation

- FastAPI routes and a command-line entry point.
- React/Vite dashboard for local repository registration, full-text search, and evidence retrieval.
- `/ask` evidence citations include a source path, line range, content hash, and indexed commit.
- SQLite persistence, FTS5 full-text search, symbol records, import edges, memory CRUD.
- Python AST symbol extraction and Python import extraction.
- Indexes are replaced atomically at the database transaction level when re-indexing.
- Local API and MCP tool access are read-only with respect to source files.

## Deliberate limits

- Semantic embeddings and model-generated explanations are not implemented.
- Symbol extraction is currently Python-specific.
- The graph records conservative static import/include/use edges for Python, JavaScript/TypeScript, Java/Kotlin, Go, C/C++, Rust, and C#. These edges are heuristic and do not constitute a complete compiler-resolved dependency graph or call graph.
- Indexing is synchronous and intended for local repositories of modest size.
- API authentication, multi-user tenancy, background jobs, and patch execution are not implemented.
