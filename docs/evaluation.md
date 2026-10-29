# Evaluation

Run `python evals/run_eval.py` for a deterministic retrieval smoke test.

The included dataset is intentionally tiny and is not a meaningful accuracy claim. Before calling the system release-ready, create a reviewed, versioned benchmark of at least 50 questions across multiple repositories and measure:
- Recall@k and MRR for evidence retrieval.
- Citation/path correctness.
- Unsupported claim and abstention rates.
- Index duration and query latency.
- Incremental re-index correctness.
- Secret exclusion and malicious repository instruction handling.

Compare a keyword baseline against any later hybrid or embedding retrieval implementation. Publish raw results and methodology; do not invent a score.
