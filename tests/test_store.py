import json

from repopilot.indexer import index_repository


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
