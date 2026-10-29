from repopilot.indexer import index_repository


def test_secret_files_are_excluded(fixture_repo):
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != ".env" for item in indexed["files"])


def test_gitignore_is_respected(fixture_repo):
    (fixture_repo / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    (fixture_repo / "private.txt").write_text("private marker", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != "private.txt" for item in indexed["files"])


def test_symlinked_files_are_excluded(fixture_repo, tmp_path):
    target = tmp_path / "outside.py"
    target.write_text("def secret_function():\n    return 'outside'\n", encoding="utf-8")
    link = fixture_repo / "linked.py"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("Symlink creation is not supported in this environment")

    indexed = index_repository(fixture_repo)
    assert all(item["path"] != "linked.py" for item in indexed["files"])
