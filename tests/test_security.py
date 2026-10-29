from repopilot.indexer import index_repository


def test_secret_files_are_excluded(fixture_repo):
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != ".env" for item in indexed["files"])


def test_gitignore_is_respected(fixture_repo):
    (fixture_repo / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    (fixture_repo / "private.txt").write_text("private marker", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != "private.txt" for item in indexed["files"])



def test_gitignore_negation_and_case_sensitivity(fixture_repo):
    (fixture_repo / ".gitignore").write_text("*.log\n!important.log\n", encoding="utf-8")
    (fixture_repo / "ignored.log").write_text("no index", encoding="utf-8")
    (fixture_repo / "important.py").write_text("include this", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "ignored.log" not in paths
    assert "important.py" in paths


def test_nested_gitignore_patterns_are_respected(fixture_repo):
    nested = fixture_repo / "src"
    nested.mkdir()
    (nested / ".gitignore").write_text("private.py\n", encoding="utf-8")
    (nested / "private.py").write_text("def secret_local(): pass\n", encoding="utf-8")
    (nested / "public.py").write_text("def public_local(): pass\n", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "src/private.py" not in paths
    assert "src/public.py" in paths


def test_symlink_escape_is_not_indexed(fixture_repo, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("def outside_secret(): pass\n", encoding="utf-8")
    link = fixture_repo / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    indexed = index_repository(fixture_repo)
    assert "linked.py" not in {item["path"] for item in indexed["files"]}


def test_safe_read_rejects_symlinked_parent_directory(fixture_repo, tmp_path):
    from repopilot.security import read_safe_text

    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "module.py"
    target.write_text("def outside_secret(): pass\n", encoding="utf-8")
    link = fixture_repo / "linked_dir"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    assert read_safe_text(link / "module.py", root=fixture_repo) is None


def test_safe_read_rejects_paths_outside_selected_root(fixture_repo, tmp_path):
    from repopilot.security import read_safe_text

    outside = tmp_path / "outside.py"
    outside.write_text("private data", encoding="utf-8")
    assert read_safe_text(outside, root=fixture_repo) is None


def test_safe_read_accepts_regular_bounded_file(fixture_repo):
    from repopilot.security import read_safe_text

    target = fixture_repo / "safe.py"
    target.write_text("def safe_function(): return 1\n", encoding="utf-8")
    content = read_safe_text(target, root=fixture_repo)
    assert content is not None
    assert content.replace("\r\n", "\n") == "def safe_function(): return 1\n"

def test_gitignore_directory_patterns_and_case_sensitivity(fixture_repo):
    (fixture_repo / ".gitignore").write_text("logs/\n", encoding="utf-8")
    ignored_dir = fixture_repo / "logs"
    ignored_dir.mkdir()
    (ignored_dir / "secret.py").write_text("def hidden(): pass\n", encoding="utf-8")
    visible_dir = fixture_repo / "logs2"
    visible_dir.mkdir()
    (visible_dir / "public.py").write_text("def visible(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "logs/secret.py" not in paths
    assert "logs2/public.py" in paths

    # A negation with different case must not re-include a case-sensitive pattern.
    (fixture_repo / ".gitignore").write_text("*.py\n!Keep.PY\n", encoding="utf-8")
    (fixture_repo / "Keep.PY").write_text("def uppercase_extension(): pass\n", encoding="utf-8")
    (fixture_repo / "keep.py").write_text("def lowercase_extension(): pass\n", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "Keep.PY" in paths
    assert "keep.py" not in paths


def test_nested_gitignore_rules_and_negations(fixture_repo):
    nested = fixture_repo / "src"
    nested.mkdir()
    (nested / ".gitignore").write_text("generated/\n*.py\n!keep.py\n", encoding="utf-8")
    generated = nested / "generated"
    generated.mkdir()
    (generated / "ignored.py").write_text("def hidden(): pass\n", encoding="utf-8")
    (nested / "drop.py").write_text("def ignored(): pass\n", encoding="utf-8")
    (nested / "keep.py").write_text("def included(): pass\n", encoding="utf-8")
    (nested / "main.py").write_text("def visible(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "src/generated/ignored.py" not in paths
    assert "src/drop.py" not in paths
    assert "src/keep.py" in paths
    assert "src/main.py" not in paths


def test_gitignore_cannot_reinclude_file_inside_ignored_parent(fixture_repo):
    (fixture_repo / ".gitignore").write_text("private/\n!private/visible.py\n", encoding="utf-8")
    private = fixture_repo / "private"
    private.mkdir()
    (private / "visible.py").write_text("def should_stay_ignored(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    assert "private/visible.py" not in {item["path"] for item in indexed["files"]}


def test_safe_read_rejects_oversized_file(fixture_repo):
    from repopilot.security import MAX_FILE_BYTES, read_safe_text

    target = fixture_repo / "large.py"
    target.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    assert read_safe_text(target, root=fixture_repo) is None


def test_safe_read_rejects_nul_bytes(fixture_repo):
    from repopilot.security import read_safe_text

    target = fixture_repo / "binary.py"
    target.write_bytes(b"def safe(): pass\x00\n")
    assert read_safe_text(target, root=fixture_repo) is None


def test_safe_read_rejects_invalid_utf8(fixture_repo):
    from repopilot.security import read_safe_text

    target = fixture_repo / "invalid.py"
    target.write_bytes(b"\xff\xfe\xfa")
    assert read_safe_text(target, root=fixture_repo) is None


def test_safe_read_rejects_secret_paths_even_when_text(fixture_repo):
    from repopilot.security import read_safe_text

    target = fixture_repo / ".env"
    target.write_text("TOKEN=must-not-be-read\n", encoding="utf-8")
    assert read_safe_text(target, root=fixture_repo) is None


def test_symlinked_root_gitignore_is_not_followed(fixture_repo, tmp_path):
    outside = tmp_path / "outside.gitignore"
    outside.write_text("*.py\n", encoding="utf-8")
    ignore_file = fixture_repo / ".gitignore"
    try:
        ignore_file.symlink_to(outside)
    except (OSError, NotImplementedError):
        return

    (fixture_repo / "visible.py").write_text("def visible(): pass\n", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    assert "visible.py" in {item["path"] for item in indexed["files"]}


def test_gitignore_escaped_comment_is_a_pattern(fixture_repo):
    (fixture_repo / ".gitignore").write_text("\\#private.py\n", encoding="utf-8")
    (fixture_repo / "#private.py").write_text("def hidden(): pass\n", encoding="utf-8")
    (fixture_repo / "public.py").write_text("def public(): pass\n", encoding="utf-8")

    from repopilot.security import _gitignore_patterns, _matches_gitignore

    patterns = _gitignore_patterns(fixture_repo)
    assert patterns == [r"\#private.py"]
    assert _matches_gitignore(fixture_repo, fixture_repo / "#private.py", patterns)

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "#private.py" not in paths
    assert "public.py" in paths


def test_root_anchored_gitignore_rule_does_not_match_nested_file(fixture_repo):
    (fixture_repo / ".gitignore").write_text("/root_only.py\n", encoding="utf-8")
    (fixture_repo / "root_only.py").write_text("def hidden_root(): pass\n", encoding="utf-8")
    nested = fixture_repo / "nested"
    nested.mkdir()
    (nested / "root_only.py").write_text("def visible_nested(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "root_only.py" not in paths
    assert "nested/root_only.py" in paths


def test_nested_gitignore_slash_pattern_is_anchored_to_its_directory(fixture_repo):
    nested = fixture_repo / "src"
    nested.mkdir()
    (nested / ".gitignore").write_text("/local.py\n", encoding="utf-8")
    (nested / "local.py").write_text("def hidden_local(): pass\n", encoding="utf-8")
    child = nested / "child"
    child.mkdir()
    (child / "local.py").write_text("def visible_child(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "src/local.py" not in paths
    assert "src/child/local.py" in paths


def test_invalid_utf8_gitignore_fails_closed_without_crashing_indexer(fixture_repo):
    (fixture_repo / ".gitignore").write_bytes(b"\xff\xfe\xfa")
    (fixture_repo / "visible.py").write_text("def visible(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    assert "visible.py" in {item["path"] for item in indexed["files"]}
