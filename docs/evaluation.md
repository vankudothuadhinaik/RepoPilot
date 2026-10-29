# Evaluation

Run the deterministic smoke check and synthetic retrieval benchmark:

```bash
python evals/run_eval.py
```

The run combines:
- A three-case wiring smoke test.
- A 51-case synthetic retrieval benchmark spanning three fixture repositories and 17 hand-authored source files: 46 positive path-retrieval queries and five negative/abstention queries.

The benchmark reports Recall@5, Recall@10, MRR@10, and abstention accuracy, plus per-query expected path and rank. CI uploads the full JSON report as a commit-specific artifact named `repopilot-retrieval-benchmark-py<version>-<sha>` for each Python matrix version for 30 days.

**Interpretation boundary:** the fixture content and queries are intentionally curated to verify deterministic lexical retrieval behavior. This is not a representative real-world corpus, a semantic retrieval benchmark, an LLM answer-quality evaluation, or a security certification. Do not present these metrics as production accuracy.

## Reviewed ground-truth check

Run the API-level source-grounded check from the repository root:

```bash
python evals/run_ground_truth.py --root .
```

The question set is [`evals/datasets/ground_truth.json`](../evals/datasets/ground_truth.json). It contains 15 reviewed questions: 13 positive cases spanning API evidence selection, symbol/import indexing, SQLite retrieval and memory persistence, filesystem safety, and provider-response validation, plus two encoded negative queries. Each positive case specifies an expected file, Python symbol, and independently checked source range. Negative query text is encoded so the dataset cannot accidentally index the literal query as evidence.

The evaluator copies the selected checkout into a temporary corpus, excludes generated reports and the literal ground-truth dataset from that copy, and registers the sanitized corpus through the real API. This prevents the evaluator from retrieving its own query/label file as evidence. It reports Recall@5, Recall@1, MRR@5, exact symbol-range accuracy, citation line correctness, unsupported-query abstention, and per-category accuracy. It checks cited line contents against the copied source, not merely whether a citation-shaped string exists. The live provider remains mocked for this deterministic test; provider-backed answer quality is measured separately in the opt-in evaluation.

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

## Multi-repository performance runs

To compare multiple local repositories with the same methodology, run:

```bash
PYTHONPATH=src python evals/benchmark_matrix.py /path/to/repo-small /path/to/repo-medium /path/to/repo-large --output benchmark-matrix.json
```

The matrix runner records each repository's file count/bytes, first scan and persistence time, unchanged incremental scan/persistence time, fixed-query median/p95 latency, database size, scan errors, and Python-tracked peak allocations. Choose repositories that you are authorized to inspect and record their provenance and machine/runtime details when publishing results. The tool does not assign size categories automatically; label categories only when the file counts/bytes and selection criteria are disclosed.

This expands the repeatable measurement workflow but does not itself supply an independently curated retrieval-question set, run an external corpus, or measure semantic citation correctness. Those require separate datasets and, for LLM metrics, controlled provider runs.


## Optional live provider evaluation

See [live provider evaluation](live-provider-evaluation.md) for the opt-in provider-backed run, report fields, secret handling, and interpretation limits. This evaluation is intentionally not required for ordinary CI because it requires a paid/external provider and repository source may be sent to that provider. Offline tests remain the deterministic baseline.

## Identifier-aware lexical ranking

The synthetic suite includes an identifier regression for `auth_token`: FTS tokenization splits identifier punctuation into searchable terms, and a bounded exact path-token boost ranks the matching implementation file above generic documentation with the same terms. The SQLite FTS path and the fallback search path use the same query-token and path-ranking policy. Punctuation-only queries return no results instead of matching every file.

This remains lexical ranking, not semantic retrieval. Review the per-query ranks in the benchmark artifact rather than treating a passing threshold as proof of broad real-world performance. The reviewed source-ground-truth set checks 13 positive questions across five implementation modules plus two unsupported queries; it is deliberately offline and does not spend provider credits. Its scope is still this repository, not an independently sampled external corpus. Provider behavior belongs to the opt-in live-provider evaluation.


## Sharing benchmark matrices safely

The matrix runner records a repository commit when available, making measurements easier to reproduce against a pinned revision. It also supports path redaction for reports that may be shared:

```bash
PYTHONPATH=src python evals/benchmark_matrix.py /path/to/repo-small /path/to/repo-medium /path/to/repo-large --redact-paths --output benchmark-matrix.json
```

Path redaction replaces absolute repository roots with `<redacted>`; it does not anonymize repository names or guarantee that every report field is safe to publish. Review output before sharing it, especially for private repository names, source-derived metadata, and scan errors. Commit identifiers and runtime measurements should be retained when reproducibility matters. A redacted report is not a substitute for permission to inspect the repositories.


## Multi-repository source-grounded evaluation

Run the pinned multi-repository evaluation locally:

```bash
PYTHONPATH=src python evals/run_multirepo_ground_truth.py --root . --output multirepo_ground_truth_results.json
```

The versioned dataset `evals/datasets/ground_truth_multirepo.json` contains 41 cases (31 positive expected-source-range cases and 10 unsupported queries) across RepoPilot and pinned source snapshots from DataPulse-Analytics, HealthStream-ETL, and low-latency-matching-engine. The snapshot commit IDs and upstream URLs are recorded in the dataset and copied into the report. The evaluator registers each corpus separately, excludes the dataset and fixture directory from the RepoPilot corpus, checks source-line snippets against the indexed snapshot, and reports Recall@1/5, MRR@5, citation-range validity, optional symbol-range accuracy, unsupported-query abstention, category breakdowns, and per-case outcomes. CI publishes the JSON report for 30 days.

**Review status:** this is a maintainer-authored evaluation set with source-range checks; the dataset explicitly records that independent second-person review is still pending. Do not call it independently reviewed until another reviewer verifies the questions and expected ranges. It also does not prove semantic entailment, represent all codebases, or replace a live-provider evaluation. The offline evaluator calls no external LLM provider and does not need API credentials.
