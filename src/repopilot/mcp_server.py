"""Optional MCP server. Install with: pip install -e '.[mcp]'."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]  # type: ignore[import-not-found]

from repopilot.store import Store

mcp = FastMCP("RepoPilot")
store = Store()


@mcp.tool()
def list_repositories() -> list[dict]:
    """List repositories indexed in the local RepoPilot database."""
    return store.list_repositories()


@mcp.tool()
def search_code(repository_id: str, query: str, limit: int = 10) -> list[dict]:
    """Search indexed repository text; returns paths and matching snippets."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if not store.repository(repository_id):
        raise ValueError("Repository not found")
    return store.search(repository_id, query, limit)


@mcp.tool()
def find_symbol(repository_id: str, query: str = "", limit: int = 50) -> list[dict]:
    """Find Python classes and functions discovered by the indexer."""
    if not store.repository(repository_id):
        raise ValueError("Repository not found")
    return store.symbols(repository_id, query or None, limit)


@mcp.tool()
def repository_overview(repository_id: str) -> dict:
    """Return repository metadata and indexing coverage."""
    repo = store.repository(repository_id)
    if not repo:
        raise ValueError("Repository not found")
    return repo


@mcp.tool()
def retrieve_memory(repository_id: str) -> list[dict]:
    """Retrieve stored engineering memories for a repository."""
    if not store.repository(repository_id):
        raise ValueError("Repository not found")
    return store.list_memories(repository_id)


if __name__ == "__main__":
    mcp.run()
