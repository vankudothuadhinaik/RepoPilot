from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from repopilot.indexer import index_repository
from repopilot.store import Store

app = FastAPI(
    title="RepoPilot API",
    version="0.1.0",
    description="Local-first, evidence-grounded repository intelligence API.",
)
store = Store()


class RegisterRepository(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=8, ge=1, le=20)
    language: str | None = None
    path_prefix: str | None = None


class MemoryCreate(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=4000)
    evidence: list[str] = Field(default_factory=list, max_length=30)
    status: str = "proposed"


class MemoryUpdate(BaseModel):
    summary: str | None = Field(default=None, max_length=4000)
    status: str | None = None


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, Any]:
    try:
        return {"status": "ready", "repositories": len(store.list_repositories())}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Storage unavailable") from exc


@app.get("/api/repos")
def list_repositories() -> list[dict[str, Any]]:
    repos = store.list_repositories()
    for repo in repos:
        repo["errors"] = json.loads(repo.pop("errors_json", "[]"))
    return repos


@app.post("/api/repos", status_code=201)
def register_repository(payload: RegisterRepository) -> dict[str, Any]:
    try:
        indexed = index_repository(payload.path)
        repo = store.index(indexed)
        repo["errors"] = json.loads(repo.pop("errors_json", "[]"))
        repo["coverage"] = indexed["coverage"]
        return repo
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def require_repo(repo_id: str) -> dict[str, Any]:
    repo = store.repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@app.get("/api/repos/{repo_id}")
def repository_detail(repo_id: str) -> dict[str, Any]:
    repo = require_repo(repo_id)
    repo["errors"] = json.loads(repo.pop("errors_json", "[]"))
    return repo


@app.post("/api/repos/{repo_id}/index")
def reindex_repository(repo_id: str) -> dict[str, Any]:
    repo = require_repo(repo_id)
    try:
        result = store.index(index_repository(repo["root_path"]))
        result["errors"] = json.loads(result.pop("errors_json", "[]"))
        return result
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/repos/{repo_id}/search")
def search_repository(repo_id: str, payload: AskRequest) -> dict[str, Any]:
    require_repo(repo_id)
    results = store.search(repo_id, payload.question, payload.limit, payload.language, payload.path_prefix)
    return {"query": payload.question, "results": results, "result_count": len(results)}


@app.post("/api/repos/{repo_id}/ask")
def ask_repository(repo_id: str, payload: AskRequest) -> dict[str, Any]:
    require_repo(repo_id)
    results = store.search(repo_id, payload.question, payload.limit, payload.language, payload.path_prefix)
    if not results:
        return {
            "answer": "I couldn't verify an answer from the indexed repository. Try a more specific identifier or re-index the current checkout.",
            "evidence": [], "abstained": True,
        }
    evidence = []
    for item in results:
        file_data = store.get_file(repo_id, item["path"])
        if not file_data:
            continue
        snippet = item.get("snippet", "")
        evidence.append({
            "path": item["path"], "language": item["language"],
            "snippet": snippet, "sha256": file_data["sha256"],
            "indexed_commit": require_repo(repo_id).get("indexed_commit"),
        })
    # No model is called here. The baseline deliberately reports retrieved evidence rather than inventing an LLM answer.
    return {
        "answer": "Retrieved repository evidence is shown below. This local baseline does not generate a semantic explanation; inspect the cited snippets before drawing conclusions.",
        "evidence": evidence, "abstained": len(evidence) == 0,
    }


@app.get("/api/repos/{repo_id}/symbols")
def symbols(repo_id: str, q: str | None = None, limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    require_repo(repo_id)
    return store.symbols(repo_id, q, limit)


@app.get("/api/repos/{repo_id}/graph")
def graph(repo_id: str, limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    require_repo(repo_id)
    return store.graph(repo_id, limit)


@app.get("/api/repos/{repo_id}/files/{file_path:path}")
def get_file(repo_id: str, file_path: str) -> dict[str, Any]:
    require_repo(repo_id)
    normalized = Path(file_path)
    if normalized.is_absolute() or ".." in normalized.parts or "\\" in file_path:
        raise HTTPException(status_code=400, detail="Invalid repository-relative path")
    result = store.get_file(repo_id, normalized.as_posix())
    if not result:
        raise HTTPException(status_code=404, detail="Indexed file not found")
    return result


@app.get("/api/repos/{repo_id}/memories")
def list_memories(repo_id: str) -> list[dict[str, Any]]:
    require_repo(repo_id)
    return store.list_memories(repo_id)


@app.post("/api/repos/{repo_id}/memories", status_code=201)
def create_memory(repo_id: str, payload: MemoryCreate) -> dict[str, Any]:
    require_repo(repo_id)
    try:
        return store.create_memory(repo_id, payload.type, payload.summary, payload.evidence, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, payload: MemoryUpdate) -> dict[str, Any]:
    try:
        result = store.update_memory(memory_id, payload.summary, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@app.delete("/api/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: str) -> None:
    if not store.delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")


@app.delete("/api/repos/{repo_id}", status_code=204)
def delete_repository(repo_id: str) -> None:
    if not store.delete_repository(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found")
