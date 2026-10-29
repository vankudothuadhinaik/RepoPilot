# Validation report

## Scope and reproducibility

P3 evaluation changes are merged in commit `81db677152e0b5ce70936cb6116c2dee6ac4ef98`. This report reflects the remote GitHub Actions run against that exact commit rather than a developer-specific local workspace.

- [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40921608962) — passed.
- [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40921608715) — passed.
- Python 3.11 and 3.12 tests passed; Ruff, Mypy, Windows security, Docker build, frontend build, and optional MCP checks passed.
- Python test summary on the Python 3.11 job: 77 passed, 1 warning; coverage report was 74% for `src/repopilot`.

## Offline source-grounded evaluation

The versioned multi-repository set has 41 cases across four pinned snapshots: 31 positive expected-range cases and 10 unsupported queries. The source revision IDs and upstream repository URLs are stored with the dataset.

| Metric | CI result |
|---|---:|
| Recall@1 | 93.55% (29/31) |
| Recall@5 | 100% (31/31) |
| MRR@5 | 0.9543 |
| Citation-range validity | 100% |
| Symbol-range accuracy | 100% (13/13 symbol cases) |
| Unsupported-query abstention | 100% (10/10) |
| Total cases passing | 41/41 |

CI publishes the JSON evaluation report and a path-redacted performance matrix for the three external source snapshots as 30-day artifacts. The matrix includes pinned source revisions, file counts/bytes, scan and incremental-index measurements, fixed-query median/p95 latency, database size, and tracked peak allocations.

These are curated, maintainer-authored cases. The dataset explicitly records that independent second-person review is pending. Citation-line validity, retrieval rank, and symbol-span checks do not prove semantic entailment or general production accuracy.

## Live provider evaluation

CI attempted the configured live-provider evaluation, but the latest report recorded 13 provider HTTP errors across 13 positive cases, a provider answer rate of 0%, and a supported-citation rate of 0%. The earlier provider response identified a `429 credit_balance_exhausted` condition. Therefore, the live-provider evaluation is **not passed**; its latency measurements reflect failed requests and local overhead, not successful model generation.

The report now includes the dataset hash/version, configured model and provider hostname, expected facts and source anchors, expected-range coverage, symbol-range checks, exact quoted-evidence support, latency median/p95, and redacted provider error/timeout categories. API credentials and raw provider error bodies are excluded. The provider's server-side model version is not exposed by the API and is not claimed.

## Remaining external validation

- Independent second-person review of all expected paths, ranges, fact anchors, and unsupported cases is still required before calling the corpus independently reviewed.
- A successful live-provider run requires valid provider credits and a rerun of the evaluation.
- No external penetration test or independent production-scale retrieval study is claimed.
