# Validation report

## Scope and reproducibility

The final local-validation workflow fix is committed on `main` as `d1acc07e1c34cd8ba9a4b6ad1d640c853756b961`. Local validation was performed on Windows 11 with Python 3.14.8 and Docker Desktop.

- The prior baseline [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370963) and [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370962) passed for `8f9a8c9`.
- The final commit's CI, CodeQL, and Codecov results are queued or in progress at the [CI workflow](https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/ci.yml?query=branch%3Amain) and [CodeQL workflow](https://github.com/vankudothuadhinaik/RepoPilot/actions/workflows/codeql.yml?query=branch%3Amain); no final remote result is claimed yet.
- Local validation passed 88 Python tests with 77% total coverage, Ruff, Mypy, compilation, the synthetic evaluator, the 15-case ground-truth evaluator, the 41-case multi-repository evaluator, the pinned snapshot performance matrix, frontend install/audit/build, Compose validation, and Docker startup/authentication checks.
- The Windows security/indexer subset passed 28 tests and covered the changed Windows descriptor path. CI now uploads Windows coverage alongside Ubuntu coverage; thresholds remain 65% project and 60% patch.

## Offline source-grounded evaluation

The versioned multi-repository set has 41 cases across four pinned snapshots: 31 positive expected-range cases and 10 unsupported queries.

| Metric | Result |
|---|---:|
| Recall@1 | 93.55% (29/31) |
| Recall@5 | 100% (31/31) |
| MRR@5 | 0.9543 |
| Citation-range validity | 100% |
| Symbol-range accuracy | 100% (13/13) |
| Unsupported-query abstention | 100% (10/10) |
| Total cases passing | 41/41 |

These are curated, maintainer-authored cases. Independent second-person review is pending; the metrics do not prove semantic entailment or production accuracy.

## Live provider evaluation

The latest provider evaluation recorded 13 provider HTTP errors across 13 positive cases, a 0% provider answer rate, and 0% supported-citation rate. The earlier provider response identified `429 credit_balance_exhausted`. The live-provider evaluation is therefore not passed. No credential or raw provider response is included in reports.

## Local deployment evidence

The deployment binds to `127.0.0.1:8010` and forwards to container port `8000`. It was rebuilt with `doppler run -- docker compose up --build -d`. Readiness returned 200; unauthenticated and wrong-token `/api/repos` returned 401; a Doppler-authenticated request returned 200 without printing the token. Restart recovery preserved data. The container ran as `appuser` with a read-only root filesystem, all capabilities dropped, no-new-privileges, `/tmp` tmpfs, and a named `/data` volume. Missing-token Compose interpolation failed closed.

## Remaining external validation

- Independent second-person review of expected paths, ranges, fact anchors, and unsupported cases remains required.
- A successful live-provider run requires valid provider credits and a rerun.
- No external penetration test or independent production-scale retrieval study is claimed.
