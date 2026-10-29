# Evaluation

Run the deterministic smoke check and synthetic retrieval benchmark:

```bash
python evals/run_eval.py
```

The run combines:
- A three-case wiring smoke test.
- A 50-case synthetic retrieval benchmark spanning three fixture repositories and 15 hand-authored source files: 45 positive path-retrieval queries and five negative/abstention queries.

The benchmark reports Recall@5, Recall@10, MRR@10, and abstention accuracy, plus per-query expected path and rank. CI uploads the full JSON report as a commit-specific artifact named `repopilot-retrieval-benchmark-py<version>-<sha>` for each Python matrix version for 30 days.

**Interpretation boundary:** the fixture content and queries are intentionally curated to verify deterministic lexical retrieval behavior. This is not a representative real-world corpus, a semantic retrieval benchmark, an LLM answer-quality evaluation, or a security certification. Do not present these metrics as production accuracy.

CI also runs `PYTHONPATH=src python evals/benchmark_repository.py .` against the checked-out RepoPilot repository. It records file count/bytes, scan and persistence durations, unchanged-tree incremental timings, fixed-query search median/p95, database size, and Python-tracked peak allocations. The JSON report is uploaded as `repopilot-repository-benchmark-py<version>-<sha>` for each Python matrix version for 30 days. This provides a reproducible baseline for this repository on the CI runner, not a multi-size or representative external-corpus benchmark. Run it on another repository with `PYTHONPATH=src python evals/benchmark_repository.py /path/to/repo --output report.json`.

Before a broader release claim, add a reviewed and independently authored question set from multiple real-but-permitted repositories and measure:
- Recall@k and MRR for evidence retrieval.
- Citation/path correctness and citation line validity.
- Unsupported claim and abstention rates for each configured LLM provider.
- Index duration, query latency, and memory use on small/medium/large repositories.
- Incremental re-index correctness, including parser-version invalidation.
- Secret exclusion and malicious repository instruction handling.
- Comparison of keyword retrieval against any later hybrid or embedding implementation.

Publish the raw results and methodology, including corpus provenance and limitations. Never invent or extrapolate a score from the synthetic benchmark.
