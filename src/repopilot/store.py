from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repopilot.config import database_path


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL UNIQUE,
                    branch TEXT, indexed_commit TEXT, status TEXT NOT NULL DEFAULT 'indexed',
                    indexed_at TEXT NOT NULL, file_count INTEGER NOT NULL DEFAULT 0,
                    symbol_count INTEGER NOT NULL DEFAULT 0, parser_version TEXT NOT NULL DEFAULT '1',
                    errors_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS files (
                    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    path TEXT NOT NULL, language TEXT NOT NULL, content TEXT NOT NULL,
                    sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                    PRIMARY KEY(repository_id, path)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS file_search USING fts5(
                    repository_id UNINDEXED, path UNINDEXED, language UNINDEXED, content,
                    tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS symbols (
                    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    name TEXT NOT NULL, qualified_name TEXT NOT NULL, kind TEXT NOT NULL,
                    path TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
                    signature TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(repository_id, name);
                CREATE TABLE IF NOT EXISTS relationships (
                    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    source TEXT NOT NULL, target TEXT NOT NULL, kind TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.5
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    type TEXT NOT NULL, summary TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '[]',
                    repository_commit TEXT, status TEXT NOT NULL DEFAULT 'proposed',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memories_repo ON memories(repository_id, updated_at);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, repository_id TEXT, action TEXT NOT NULL,
                    target TEXT, outcome TEXT NOT NULL, created_at TEXT NOT NULL, details_json TEXT NOT NULL
                );
            """)
            repository_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(repositories)").fetchall()
            }
            if "parser_version" not in repository_columns:
                db.execute(
                    "ALTER TABLE repositories ADD COLUMN parser_version TEXT NOT NULL DEFAULT '1'"
                )

    def audit(self, repository_id: str | None, action: str, target: str | None,
              outcome: str, details: dict[str, Any] | None = None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), repository_id, action, target, outcome, now(),
                 json.dumps(details or {})),
            )

    def index(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a repository snapshot while only rewriting changed file records.

        The indexer currently scans the working tree to calculate hashes. This method
        avoids replacing unchanged SQLite/FTS rows and only rebuilds symbols/imports
        for files whose content changed, plus removing files no longer present.
        """
        with self.connect() as db:
            existing = db.execute(
                "SELECT id, parser_version FROM repositories WHERE root_path=?", (data["root"],)
            ).fetchone()
            parser_version = str(data.get("parser_version", "1"))
            parser_changed = existing is not None and existing["parser_version"] != parser_version
            repo_id = existing["id"] if existing else str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO repositories(id,name,root_path,branch,indexed_commit,status,indexed_at,
                    file_count,symbol_count,parser_version,errors_json)
                VALUES(?,?,?,?,?,'indexed',?,?,?,?,?)
                ON CONFLICT(root_path) DO UPDATE SET
                    name=excluded.name, branch=excluded.branch, indexed_commit=excluded.indexed_commit,
                    status='indexed', indexed_at=excluded.indexed_at, file_count=excluded.file_count,
                    symbol_count=excluded.symbol_count, parser_version=excluded.parser_version,
                    errors_json=excluded.errors_json
                """,
                (
                    repo_id, data["name"], data["root"], data["branch"], data["commit"], now(),
                    len(data["files"]), len(data["symbols"]), parser_version, json.dumps(data["errors"]),
                ),
            )
            repo_id = db.execute(
                "SELECT id FROM repositories WHERE root_path=?", (data["root"],)
            ).fetchone()["id"]

            incoming = {item["path"]: item for item in data["files"]}
            current_rows = db.execute(
                "SELECT path, sha256 FROM files WHERE repository_id=?", (repo_id,)
            ).fetchall()
            current = {row["path"]: row["sha256"] for row in current_rows}
            removed = set(current) - set(incoming)
            changed = {
                path for path, item in incoming.items()
                if current.get(path) != item["sha256"]
            }
            if parser_changed:
                # Rebuild derived records after parser behavior changes even when file bytes do not.
                changed = set(incoming)

            # Delete removed files and all derived rows tied to those paths.
            for path in sorted(removed):
                db.execute("DELETE FROM file_search WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM files WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM symbols WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM relationships WHERE repository_id=? AND source=?", (repo_id, path))

            # Rewrite only changed/new file bodies and their derived indexes.
            symbols_by_path: dict[str, list[dict[str, Any]]] = {}
            for symbol in data["symbols"]:
                symbols_by_path.setdefault(symbol["path"], []).append(symbol)
            imports_by_path: dict[str, list[dict[str, str]]] = {}
            for relation in data["imports"]:
                imports_by_path.setdefault(relation["source"], []).append(relation)

            for path in sorted(changed):
                item = incoming[path]
                db.execute("DELETE FROM file_search WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM files WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM symbols WHERE repository_id=? AND path=?", (repo_id, path))
                db.execute("DELETE FROM relationships WHERE repository_id=? AND source=?", (repo_id, path))
                db.execute(
                    "INSERT INTO files VALUES (?,?,?,?,?,?)",
                    (repo_id, path, item["language"], item["content"], item["sha256"], item["size_bytes"]),
                )
                db.execute(
                    "INSERT INTO file_search VALUES (?,?,?,?)",
                    (repo_id, path, item["language"], item["content"]),
                )
                for symbol in symbols_by_path.get(path, []):
                    db.execute(
                        "INSERT INTO symbols VALUES (?,?,?,?,?,?,?,?)",
                        (
                            repo_id, symbol["name"], symbol["qualified_name"], symbol["kind"],
                            symbol["path"], symbol["start_line"], symbol["end_line"], symbol["signature"],
                        ),
                    )
                for relation in imports_by_path.get(path, []):
                    db.execute(
                        "INSERT INTO relationships VALUES (?,?,?,?,?)",
                        (repo_id, relation["source"], relation["target"], relation["kind"], 0.7),
                    )

            added = set(incoming) - set(current)
            updated = changed - added
            delta = {
                "added": len(added),
                "updated": len(updated),
                "removed": len(removed),
                "unchanged": len(incoming) - len(changed),
                "files_scanned": len(incoming),
            }
            timestamp = now()
            db.execute(
                "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), repo_id, "index_repository", data["root"], "success",
                    timestamp,
                    json.dumps({
                        "files": len(incoming),
                        "changed": len(changed),
                        "added": len(added),
                        "updated": len(updated),
                        "removed": len(removed),
                        "unchanged": len(incoming) - len(changed),
                        "symbols_parsed": len(data["symbols"]),
                    }),
                ),
            )
            symbol_count = db.execute(
                "SELECT COUNT(*) AS count FROM symbols WHERE repository_id=?", (repo_id,)
            ).fetchone()["count"]
            db.execute(
                "UPDATE repositories SET file_count=?, symbol_count=? WHERE id=?",
                (len(incoming), symbol_count, repo_id),
            )
            row = dict(db.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone())
            row["index_delta"] = delta
            return row

    def file_hashes(self, root_path: str | Path) -> dict[str, str]:
        """Return indexed content hashes for a repository root, if registered."""
        canonical_root = str(Path(root_path).expanduser().resolve())
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM repositories WHERE root_path=?", (canonical_root,)
            ).fetchone()
            if not row:
                return {}
            rows = db.execute(
                "SELECT path, sha256 FROM files WHERE repository_id=?", (row["id"],)
            ).fetchall()
            return {item["path"]: item["sha256"] for item in rows}

    def parser_version_for_root(self, root_path: str | Path) -> str | None:
        """Return the parser version used for the indexed repository at this root."""
        canonical_root = str(Path(root_path).expanduser().resolve())
        with self.connect() as db:
            row = db.execute(
                "SELECT parser_version FROM repositories WHERE root_path=?", (canonical_root,)
            ).fetchone()
            return str(row["parser_version"]) if row else None

    def list_repositories(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM repositories ORDER BY name")]

    def repository(self, repo_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone()
            return dict(row) if row else None

    def search(self, repo_id: str, query: str, limit: int = 10, language: str | None = None,
               path_prefix: str | None = None) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        limit = max(1, min(limit, 50))
        prefix = path_prefix.strip("/") if path_prefix else None
        if prefix is not None and (not prefix or "\\" in prefix or ".." in prefix.split("/")):
            return []
        with self.connect() as db:
            # FTS syntax is user-controlled; quote tokens so punctuation does not become operators.
            tokens = [part.replace('"', '""') for part in query.split() if part]
            fts_query = " AND ".join(f'"{token}"' for token in tokens)
            clauses = ["repository_id=?", "file_search MATCH ?"]
            params: list[Any] = [repo_id, fts_query]
            if language:
                clauses.append("language=?")
                params.append(language)
            if prefix:
                clauses.append("(path=? OR substr(path,1,length(?)+1)=? || '/')")
                params.extend([prefix, prefix, prefix])
            sql = f"""
                SELECT path, language, snippet(file_search, 3, '[', ']', ' … ', 12) AS snippet,
                       bm25(file_search) AS rank
                FROM file_search WHERE {" AND ".join(clauses)}
                ORDER BY rank LIMIT ?
            """
            params.append(limit)
            try:
                rows = db.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return self._fallback_search(db, repo_id, query, limit, language, prefix)
            return [{**dict(row), "rank": float(row["rank"])} for row in rows]

    def _fallback_search(self, db: sqlite3.Connection, repo_id: str, query: str, limit: int,
                         language: str | None, path_prefix: str | None) -> list[dict[str, Any]]:
        rows = db.execute(
            "SELECT path,language,content FROM files WHERE repository_id=?", (repo_id,)
        ).fetchall()
        result = []
        terms = query.casefold().split()
        for row in rows:
            path = row["path"]
            if language and row["language"] != language:
                continue
            if path_prefix and not (
                path == path_prefix or path.startswith(path_prefix + "/")
            ):
                continue
            content = row["content"]
            if all(term in content.casefold() for term in terms):
                result.append({
                    "path": path, "language": row["language"],
                    "snippet": content[:500], "rank": 0.0,
                })
            if len(result) >= limit:
                break
        return result

    def symbols(self, repo_id: str, query: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as db:
            if query:
                rows = db.execute("""
                    SELECT name,qualified_name,kind,path,start_line,end_line,signature
                    FROM symbols WHERE repository_id=? AND name LIKE ? ORDER BY name LIMIT ?
                """, (repo_id, f"%{query}%", max(1, min(limit, 200)))).fetchall()
            else:
                rows = db.execute("""
                    SELECT name,qualified_name,kind,path,start_line,end_line,signature
                    FROM symbols WHERE repository_id=? ORDER BY path,start_line LIMIT ?
                """, (repo_id, max(1, min(limit, 200)))).fetchall()
            return [dict(row) for row in rows]

    def get_file(self, repo_id: str, path: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT path,language,content,sha256 FROM files WHERE repository_id=? AND path=?",
                             (repo_id, path)).fetchone()
            return dict(row) if row else None

    def graph(self, repo_id: str, limit: int = 100) -> dict[str, Any]:
        with self.connect() as db:
            rows = db.execute("SELECT source,target,kind,confidence FROM relationships WHERE repository_id=? LIMIT ?",
                              (repo_id, max(1, min(limit, 500)))).fetchall()
            return {"edges": [dict(row) for row in rows],
                    "note": "Python imports are extracted statically; import targets are not guaranteed to resolve."}

    def create_memory(self, repo_id: str, kind: str, summary: str, evidence: list[str],
                      status: str = "proposed") -> dict[str, Any]:
        memory_id = str(uuid.uuid4())
        repo = self.repository(repo_id)
        if not repo:
            raise KeyError("Repository not found")
        if status not in {"proposed", "verified", "superseded", "rejected"}:
            raise ValueError("Invalid memory status")
        timestamp = now()
        with self.connect() as db:
            db.execute("INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?)",
                (memory_id, repo_id, kind, summary, json.dumps(evidence), repo.get("indexed_commit"),
                 status, timestamp, timestamp))
            db.execute("INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), repo_id, "create_memory", memory_id, "success", timestamp,
                 json.dumps({"status": status})))
            row = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            return dict(row)

    def list_memories(self, repo_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM memories WHERE repository_id=? ORDER BY updated_at DESC",
                              (repo_id,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["evidence"] = json.loads(item.pop("evidence_json"))
                result.append(item)
            return result

    def update_memory(self, memory_id: str, summary: str | None = None,
                      status: str | None = None) -> dict[str, Any] | None:
        if status and status not in {"proposed", "verified", "superseded", "rejected"}:
            raise ValueError("Invalid memory status")
        with self.connect() as db:
            row = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                return None
            new_summary = summary if summary is not None else row["summary"]
            new_status = status if status is not None else row["status"]
            db.execute("UPDATE memories SET summary=?,status=?,updated_at=? WHERE id=?",
                       (new_summary, new_status, now(), memory_id))
            updated = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            return dict(updated)

    def delete_memory(self, memory_id: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT repository_id FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                return False
            db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            db.execute("INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), row["repository_id"], "delete_memory", memory_id, "success", now(), "{}"))
            return True

    def delete_repository(self, repo_id: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT id FROM repositories WHERE id=?", (repo_id,)).fetchone()
            if not row:
                return False
            db.execute("DELETE FROM file_search WHERE repository_id=?", (repo_id,))
            db.execute("DELETE FROM repositories WHERE id=?", (repo_id,))
            return True
