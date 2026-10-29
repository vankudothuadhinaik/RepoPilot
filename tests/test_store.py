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

def test_reindex_reports_file_delta_and_preserves_unchanged_files(fixture_repo, store):
    first = store.index(index_repository(fixture_repo))
    assert first["index_delta"] == {
        "added": 3,
        "updated": 0,
        "removed": 0,
        "unchanged": 0,
        "files_scanned": 3,
    }
    repo_id = first["id"]

    (fixture_repo / "app.py").write_text(
        "def replacement():\\n    return 'changed'\\n",
        encoding="utf-8",
    )
    (fixture_repo / "settings.py").unlink()
    (fixture_repo / "new_module.py").write_text(
        "def fresh_symbol():\\n    return True\\n",
        encoding="utf-8",
    )

    second = store.index(index_repository(fixture_repo))

    assert second["id"] == repo_id
    assert second["index_delta"] == {
        "added": 1,
        "updated": 1,
        "removed": 1,
        "unchanged": 1,
        "files_scanned": 3,
    }
    assert store.get_file(repo_id, "settings.py") is None
    assert store.get_file(repo_id, "new_module.py") is not None
    names = {item["name"] for item in store.symbols(repo_id)}
    assert "replacement" in names
    assert "fresh_symbol" in names
    assert "greet" not in names
    assert store.search(repo_id, "changed")
    assert not store.search(repo_id, "not-a-real-secret")
