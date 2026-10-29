# Validation report

## Scope and reproducibility

P0 hardening and P3 evaluation changes are present on `main` at commit `8f9a8c92385c1fd23156f0e5fa32bf7673842574`; the validation metadata/type follow-up is committed as `b6e097235e597d487e25bd07f851ee546cffb38e`. The local release-validation run below was performed on Windows 11 with Python 3.14.8 and Docker Desktop against that follow-up checkout.

- [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370963) — passed; the optional live-provider step produced a failed provider report as expected and is non-blocking.
- [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370962) — passed.
- The remote CI and CodeQL runs linked above passed for the P3 baseline. The local run passed 88 Python tests, Ruff, Mypy, compilation, the synthetic evaluator, the 15-case in-repository ground-truth evaluator, the 41-case multi-repository evaluator, the pinned snapshot performance matrix, frontend `npm ci`, `npm audit`, frontend production build, Compose validation, and Docker startup/authentication checks.
- The local test run used Python 3.14.8; coverage was not collected in this validation pass.

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

## Local deployment evidence

The verified local deployment binds only to `127.0.0.1:8010` and forwards to container port `8000`. It was rebuilt and started with `doppler run -- docker compose up --build -d`. Readiness returned HTTP 200; unauthenticated and wrong-token `/api/repos` requests returned HTTP 401; a request using the Doppler-provided token returned HTTP 200 without printing the token. Restart recovery preserved the indexed repository. The container ran as `appuser` with a read-only root filesystem, all capabilities dropped, no-new-privileges, `/tmp` tmpfs, and the named `/data` volume.

Missing-token Compose interpolation failed closed. These checks are local deployment evidence, not an external penetration test or production-scale assurance.
