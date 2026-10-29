# Validation report

## Scope and reproducibility

The audited baseline was `8645ac8fd28ba14365a0e61269bee015eb3db778` on `main`. Local validation was performed on Windows 11 with Python 3.14.8 and Docker Desktop. Dataset corrections and evaluator corpus-isolation fixes are recorded in `docs/evaluation_audit.md` and the associated follow-up commit.

- The prior baseline [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370963) and [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40926370962) passed for `8f9a8c9`.
- Remote CI, CodeQL, and Codecov status was not re-queried during this local audit; no current remote result is claimed here. The workflow URLs in this document are entry points, not evidence for this uncommitted review tree.
- Local validation passed the previously recorded 88 Python tests with 77% total coverage, Ruff, Mypy, compilation, the synthetic evaluator, frontend install/audit/build, Compose validation, and Docker startup/authentication checks. The focused post-audit suite passed 14 tests; the corrected 15-case evaluator passed 15/15 and the corrected 41-case evaluator passed 41/41. The complete rerun evidence and metric denominators are in [the evaluation audit](evaluation_audit.md).
- The Windows security/indexer subset passed 28 tests and covered the changed Windows descriptor path. CI now uploads Windows coverage alongside Ubuntu coverage; thresholds remain 65% project and 60% patch.

## Offline source-grounded evaluation

The versioned multi-repository set has 41 cases across four recorded source revisions: 31 positive expected-range cases and 10 unsupported queries. Three external snapshots are materialized from embedded snapshot metadata; the RepoPilot entry is materialized from its recorded Git revision by default, with checkout-relative evaluation available only through the explicit `--use-checkout` option.

| Metric | Result |
|---|---:|
| Recall@1 | 93.55% (29/31) |
| Recall@5 | 100% (31/31) |
| MRR@5 | 0.9543 |
| Citation-range validity | 100% |
| Symbol-range accuracy | 100% (13/13) |
| Unsupported-query abstention | 100% (10/10) |
| Total cases passing | 41/41 |

These are curated, maintainer-authored cases. The audit corrected an overclaimed fact, expanded abbreviated source metadata, removed one duplicate positive, replaced two lexically ambiguous negative queries, and fixed evaluator self-reference of the audit report. Independent second-person review is pending; the metrics do not prove semantic entailment or production accuracy.

## Live provider evaluation

The latest provider evaluation recorded 13 provider HTTP errors across 13 positive cases, a 0% provider answer rate, and 0% supported-citation rate. The earlier provider response identified `429 credit_balance_exhausted`. The live-provider evaluation is therefore not passed. No credential or raw provider response is included in reports.

## Local deployment evidence

The deployment binds to `127.0.0.1:8010` and forwards to container port `8000`. It was rebuilt with `doppler run -- docker compose up --build -d`. Readiness returned 200; unauthenticated and wrong-token `/api/repos` returned 401; a Doppler-authenticated request returned 200 without printing the token. Restart recovery preserved data. The container ran as `appuser` with a read-only root filesystem, all capabilities dropped, no-new-privileges, `/tmp` tmpfs, and a named `/data` volume. Missing-token Compose interpolation failed closed.

## Remaining external validation

- Independent second-person review of expected paths, ranges, fact anchors, and unsupported cases remains required.
- A successful live-provider run requires valid provider credits and a rerun.
- No external penetration test or independent production-scale retrieval study is claimed.
