from __future__ import annotations

import json

import pytest

from evals.multirepo_corpus import _citation_matches_source, _query


def test_multirepo_dataset_has_required_coverage_and_pinned_sources():
    dataset = json.loads(
        __import__("pathlib").Path("evals/datasets/ground_truth_multirepo.json").read_text(
            encoding="utf-8"
        )
    )
    questions = dataset["questions"]
    positives = [item for item in questions if item.get("expected_path")]
    negatives = [item for item in questions if not item.get("expected_path")]

    assert len(positives) >= 30
    assert len(negatives) >= 10
    assert len({item["repository"] for item in questions}) >= 4
    assert all(item.get("commit") for item in dataset["repositories"])
    assert dataset["authoring"]["independent_review_status"] == "pending"
    assert all(item.get("expected_start_line") and item.get("expected_end_line") for item in positives)


def test_single_repo_ground_truth_pins_each_question_revision():
    from pathlib import Path

    dataset = json.loads(
        Path("evals/datasets/ground_truth.json").read_text(encoding="utf-8")
    )
    revisions = {item.get("source_revision") for item in dataset["questions"]}
    assert len(revisions) >= 2
    assert all(
        isinstance(revision, str)
        and len(revision) == 40
        and all(character in "0123456789abcdef" for character in revision.lower())
        for revision in revisions
    )


def test_encoded_negative_query_decodes():
    assert _query({"query_codepoints": [110, 111, 112, 101]}) == "nope"
    assert _query({"query": "exact query"}) == "exact query"


def test_citation_range_checks_exact_source_lines_and_rejects_traversal(tmp_path):
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir()
    source.write_text("def answer():\n    return 42\n", encoding="utf-8")
    valid = {
        "path": "src/sample.py",
        "start_line": 1,
        "end_line": 2,
        "snippet": "1: def answer():\n2:     return 42",
    }
    assert _citation_matches_source(valid, tmp_path)
    assert not _citation_matches_source({**valid, "snippet": "1: forged"}, tmp_path)
    assert not _citation_matches_source({**valid, "path": "../secret"}, tmp_path)


def test_clean_root_excludes_all_ground_truth_and_fixture_data(tmp_path):
    from evals.multirepo_corpus import _clean_root

    root = tmp_path / "checkout"
    (root / "evals" / "datasets").mkdir(parents=True)
    (root / "evals" / "corpora" / "sample").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "README.md").write_text("# Fixture checkout\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "evaluation_audit.md").write_text(
        "ground-truth labels and unsupported query text", encoding="utf-8"
    )
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / "evals" / "datasets" / "ground_truth.json").write_text("{}", encoding="utf-8")
    (root / "evals" / "datasets" / "ground_truth_multirepo.json").write_text("{}", encoding="utf-8")
    (root / "evals" / "corpora" / "sample" / "source.py").write_text("secret fixture", encoding="utf-8")
    destination = tmp_path / "sanitized"
    _clean_root(root, destination)

    assert (destination / "src" / "app.py").is_file()
    assert not (destination / "evals" / "datasets" / "ground_truth.json").exists()
    assert not (destination / "evals" / "datasets" / "ground_truth_multirepo.json").exists()
    assert not (destination / "evals" / "corpora").exists()
    assert not (destination / "docs" / "evaluation_audit.md").exists()


def test_repo_pilot_materializes_recorded_revision_and_rejects_missing_revision(tmp_path):
    import subprocess
    from pathlib import Path

    from evals.multirepo_corpus import _prepare_corpus

    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    metadata = {"id": "RepoPilot", "commit": revision}
    destination = _prepare_corpus(root, "RepoPilot", metadata, tmp_path / "eval")

    assert (destination / "src" / "repopilot").is_dir()
    assert not (destination / ".git").exists()
    assert not (destination / "evals" / "datasets" / "ground_truth.json").exists()
    assert not (destination / "docs" / "evaluation_audit.md").exists()
    assert not (destination / "evals" / "corpora").exists()

    with pytest.raises(ValueError, match="required RepoPilot source revision"):
        _prepare_corpus(
            root,
            "RepoPilot",
            {"id": "RepoPilot", "commit": "0" * 40},
            tmp_path / "missing",
        )


def test_materialize_snapshot_checks_revision_and_rejects_traversal(tmp_path):
    import json

    from evals.multirepo_corpus import _materialize_snapshot

    source_root = tmp_path / "snapshot"
    source_root.mkdir()
    metadata = {
        "id": "sample",
        "commit": "abc123",
        "upstream": "https://example.invalid/sample",
    }
    (source_root / "snapshot.json").write_text(
        json.dumps(
            {
                "commit": "abc123",
                "upstream": "https://example.invalid/sample",
                "files": {"README.md": "# Source snapshot\n", "src/a.py": "def main():\n    return 1\n"},
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "materialized"
    _materialize_snapshot(source_root, destination, metadata)
    assert (destination / "src" / "a.py").is_file()

    with pytest.raises(ValueError, match="pinned source revision mismatch"):
        _materialize_snapshot(
            source_root,
            tmp_path / "wrong-revision",
            {**metadata, "commit": "different"},
        )
