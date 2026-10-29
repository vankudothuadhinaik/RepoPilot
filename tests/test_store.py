import json

from repopilot.indexer import PARSER_VERSION, index_repository
from repopilot.store import Store


def test_index_search_symbols_and_memory(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    repo_id = repo["id"]
    assert store.search(repo_id, "greet")
    assert any(item["name"] == "Service" for item in store.symbols(repo_id))
    memory = store.create_memory(repo_id, "decision", "Use SQLite for local metadata", ["README.md"])
    assert memory["status"] == "proposed"
    assert store.list_memories(repo_id)[0]["summary"] == "Use SQLite for local metadata"
    assert store.update_memory(memory["id"], status="verified")["status"] == "verified"
    assert store.delete_memory(memory["id"])
    assert not store.delete_memory(memory["id"])


def test_reindex_replaces_old_file_contents(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    (fixture_repo / "app.py").write_text("def new_name():\n    return 1\n", encoding="utf-8")
    store.index(index_repository(fixture_repo))
    names = {item["name"] for item in store.symbols(repo["id"])}
    assert "new_name" in names
    assert "greet" not in names

def test_incremental_reindex_updates_only_changed_and_removed_files(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    repo_id = repo["id"]
    assert repo["index_delta"] == {
        "added": 3, "updated": 0, "removed": 0, "unchanged": 0, "files_scanned": 3,
    }

    (fixture_repo / "app.py").write_text("def renamed_symbol():\n    return 'fresh-token'\n", encoding="utf-8")
    (fixture_repo / "README.md").unlink()
    updated = store.index(index_repository(fixture_repo))

    assert updated["index_delta"] == {
        "added": 0, "updated": 1, "removed": 1, "unchanged": 1, "files_scanned": 2,
    }
    symbols = {item["name"] for item in store.symbols(repo_id)}
    assert "renamed_symbol" in symbols
    assert "greet" not in symbols
    assert store.get_file(repo_id, "README.md") is None
    assert store.search(repo_id, "fresh-token")
    assert not store.search(repo_id, "greet")

    with store.connect() as db:
        event = db.execute(
            "SELECT details_json FROM audit_events WHERE repository_id=? AND action='index_repository' "
            "ORDER BY created_at DESC LIMIT 1",
            (repo_id,),
        ).fetchone()
    details = json.loads(event["details_json"])
    assert details["changed"] >= 1
    assert details["removed"] == 1


def test_incremental_reindex_keeps_unchanged_files_searchable(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    repo_id = repo["id"]
    original = store.get_file(repo_id, "app.py")

    store.index(index_repository(fixture_repo))

    assert store.get_file(repo_id, "app.py")["sha256"] == original["sha256"]
    with store.connect() as db:
        event = db.execute(
            "SELECT details_json FROM audit_events WHERE repository_id=? AND action='index_repository' "
            "ORDER BY created_at DESC LIMIT 1",
            (repo_id,),
        ).fetchone()
    import json
    details = json.loads(event["details_json"])
    assert details["changed"] == 0
    assert details["removed"] == 0



def test_search_filters_are_applied_before_limit_and_use_directory_boundaries(fixture_repo, store):
    (fixture_repo / "src").mkdir()
    (fixture_repo / "src" / "target.py").write_text("def marker_target():\n    return 'marker'\n", encoding="utf-8")
    (fixture_repo / "src-old").mkdir()
    (fixture_repo / "src-old" / "target.py").write_text("def marker_old():\n    return 'marker'\n", encoding="utf-8")
    repo = store.index(index_repository(fixture_repo))

    results = store.search(repo["id"], "marker", limit=1, language="python", path_prefix="src")

    assert len(results) == 1
    assert results[0]["path"] == "src/target.py"
    assert store.search(repo["id"], "marker", path_prefix="../src") == []

def test_parser_version_is_persisted_and_exposed(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    assert repo["parser_version"] == PARSER_VERSION
    assert store.parser_version_for_root(fixture_repo) == PARSER_VERSION



def test_parser_upgrade_rebuilds_derived_symbols_and_imports(fixture_repo, store):
    data = index_repository(fixture_repo)
    repo = store.index(data)
    repo_id = repo["id"]
    with store.connect() as db:
        before_symbols = db.execute(
            "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (repo_id,)
        ).fetchone()[0]
    assert before_symbols > 0

    # Same file hashes, newer parser version and regenerated output.
    data["parser_version"] = "future-parser-test"
    data["symbols"] = [
        {
            "name": "new_parser_symbol", "qualified_name": "new_parser_symbol",
            "kind": "function", "path": "app.py", "start_line": 1, "end_line": 1,
            "signature": "new_parser_symbol()",
        }
    ]
    data["imports"] = [
        {"source": "app.py", "target": "new_module", "kind": "import"}
    ]
    updated = store.index(data)
    assert updated["parser_version"] == "future-parser-test"
    assert any(item["name"] == "new_parser_symbol" for item in store.symbols(repo_id))
    assert not any(item["name"] == "greet" for item in store.symbols(repo_id))
    assert any(edge["target"] == "new_module" for edge in store.graph(repo_id)["edges"])



def test_partial_index_scan_does_not_delete_unseen_files_or_advance_parser_version(fixture_repo, store):
    initial = index_repository(fixture_repo)
    repo = store.index(initial)
    repo_id = repo["id"]
    previous_version = repo["parser_version"]
    previous_files = {item["path"] for item in initial["files"]}
    assert "README.md" in previous_files

    partial = {
        **initial,
        "parser_version": "parser-next",
        "files": [item for item in initial["files"] if item["path"] != "README.md"],
        "symbols": [],
        "imports": [],
        "errors": [{"path": "README.md", "error": "transient read error"}],
    }
    result = store.index(partial)
    assert result["status"] == "partial"
    assert result["parser_version"] == previous_version
    assert store.get_file(repo_id, "README.md") is not None
    assert result["file_count"] == len(previous_files)
    with store.connect() as db:
        outcome = db.execute(
            "SELECT outcome FROM audit_events WHERE repository_id=? AND action='index_repository' "
            "ORDER BY created_at DESC LIMIT 1",
            (repo_id,),
        ).fetchone()["outcome"]
    assert outcome == "partial"



def test_failed_index_transaction_rolls_back_repository_and_rows(fixture_repo, store):
    data = index_repository(fixture_repo)
    assert data["files"]
    data["files"][0].pop("size_bytes")
    try:
        store.index(data)
    except KeyError as exc:
        assert exc.args == ("size_bytes",)
    else:
        raise AssertionError("malformed snapshot should fail")
    assert store.list_repositories() == []
    with store.connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_repository_deletion_cleans_fts_and_cascades_related_rows(fixture_repo, store):
    repo = store.index(index_repository(fixture_repo))
    repo_id = repo["id"]
    store.create_memory(repo_id, "decision", "temporary", ["README.md"])
    assert store.delete_repository(repo_id)
    assert store.repository(repo_id) is None
    assert store.search(repo_id, "greet") == []
    with store.connect() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM file_search WHERE repository_id=?", (repo_id,)
        ).fetchone()[0] == 0
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_symbol_search_matches_qualified_name_signature_kind_and_path(fixture_repo, store):
    (fixture_repo / "src").mkdir()
    (fixture_repo / "src" / "services.py").write_text(
        "class BillingService:\n"
        "    def charge(self, account_id: str) -> bool:\n"
        "        return bool(account_id)\n\n"
        "class UserService:\n"
        "    def charge(self, user_id: str) -> bool:\n"
        "        return bool(user_id)\n",
        encoding="utf-8",
    )
    repo = store.index(index_repository(fixture_repo))
    repo_id = repo["id"]

    qualified = store.symbols(repo_id, "BillingService.charge")
    assert len(qualified) == 1
    assert qualified[0]["qualified_name"] == "BillingService.charge"

    by_signature = store.symbols(repo_id, "account_id: str")
    assert any(item["qualified_name"] == "BillingService.charge" for item in by_signature)

    by_kind = store.symbols(repo_id, "class")
    assert any(item["name"] == "BillingService" for item in by_kind)

    by_path = store.symbols(repo_id, "src/services.py")
    assert len(by_path) == 4


def test_concurrent_same_snapshot_indexing_preserves_sqlite_integrity(fixture_repo, store):
    from concurrent.futures import ThreadPoolExecutor

    snapshot = index_repository(fixture_repo)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.index(snapshot), range(8)))

    repo_ids = {result["id"] for result in results}
    assert len(repo_ids) == 1
    repo_id = repo_ids.pop()
    assert store.get_file(repo_id, "app.py") is not None
    with store.connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_legacy_database_schema_is_upgraded(tmp_path):
    import sqlite3

    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("""
            CREATE TABLE repositories (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL UNIQUE,
                branch TEXT, indexed_commit TEXT, status TEXT NOT NULL DEFAULT 'indexed',
                indexed_at TEXT NOT NULL, file_count INTEGER NOT NULL DEFAULT 0,
                symbol_count INTEGER NOT NULL DEFAULT 0, errors_json TEXT NOT NULL DEFAULT '[]'
            )
        """)
        db.execute("""
            INSERT INTO repositories(id,name,root_path,indexed_at)
            VALUES ('legacy-id','legacy','/legacy','2025-01-01T00:00:00+00:00')
        """)

    upgraded = Store(database)
    assert upgraded.repository("legacy-id")["parser_version"] == "1"
    with upgraded.connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(repositories)")}
    assert "parser_version" in columns


def test_concurrent_indexing_from_separate_store_instances(fixture_repo, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    database = tmp_path / "shared.sqlite3"
    stores = [Store(database) for _ in range(4)]
    snapshot = index_repository(fixture_repo)

    def persist(index):
        return stores[index % len(stores)].index(snapshot)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(persist, range(12)))

    assert len({result["id"] for result in results}) == 1
    repo_id = results[-1]["id"]
    assert stores[0].get_file(repo_id, "app.py") is not None
    with stores[0].connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

def test_concurrent_full_scans_and_reindexes_preserve_integrity(fixture_repo, store):
    from concurrent.futures import ThreadPoolExecutor

    def scan_and_index(_):
        return store.index(index_repository(fixture_repo))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(scan_and_index, range(4)))

    repo_ids = {result["id"] for result in results}
    assert len(repo_ids) == 1
    repo_id = repo_ids.pop()
    assert store.get_file(repo_id, "app.py") is not None
    with store.connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []

def test_search_normalizes_identifier_tokens_and_boosts_matching_paths(fixture_repo, store):
    (fixture_repo / "src").mkdir()
    (fixture_repo / "docs").mkdir()
    (fixture_repo / "src" / "auth_token.py").write_text(
        "def auth_token():\n    return 'auth token implementation'\n", encoding="utf-8"
    )
    (fixture_repo / "docs" / "guide.md").write_text(
        "The auth token configuration guide explains the auth token workflow.\n",
        encoding="utf-8",
    )
    repo = store.index(index_repository(fixture_repo))

    results = store.search(repo["id"], "auth_token", limit=5)

    assert results
    assert results[0]["path"] == "src/auth_token.py"
    assert any(item["path"] == "docs/guide.md" for item in results)
    assert store.search(repo["id"], "auth_token", limit=1)[0]["path"] == "src/auth_token.py"

def test_fallback_search_uses_same_path_boost_and_ignores_punctuation_only_queries(fixture_repo, store):
    (fixture_repo / "src").mkdir()
    (fixture_repo / "docs").mkdir()
    (fixture_repo / "src" / "auth_token.py").write_text(
        "def auth_token():\n    return 'auth token implementation'\n", encoding="utf-8"
    )
    (fixture_repo / "docs" / "guide.md").write_text(
        "The auth token configuration guide explains the auth token workflow.\n",
        encoding="utf-8",
    )
    repo = store.index(index_repository(fixture_repo))

    assert store.search(repo["id"], "!!!") == []
    with store.connect() as db:
        results = store._fallback_search(db, repo["id"], "auth_token", 5, None, None)

    assert results[0]["path"] == "src/auth_token.py"
    assert any(item["path"] == "docs/guide.md" for item in results)
