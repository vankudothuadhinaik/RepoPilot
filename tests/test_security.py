from repopilot.indexer import index_repository


def test_secret_files_are_excluded(fixture_repo):
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != ".env" for item in indexed["files"])


def test_gitignore_is_respected(fixture_repo):
    (fixture_repo / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    (fixture_repo / "private.txt").write_text("private marker", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != "private.txt" for item in indexed["files"])
