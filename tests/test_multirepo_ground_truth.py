from __future__ import annotations

import json

from evals.run_multirepo_ground_truth import _citation_matches_source, _query


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
    from pathlib import Path

    from evals.run_multirepo_ground_truth import _clean_root

    root = tmp_path / "checkout"
    (root / "evals" / "datasets").mkdir(parents=True)
    (root / "evals" / "corpora" / "sample").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "README.md").write_text("# Fixture checkout\n", encoding="utf-8")
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
