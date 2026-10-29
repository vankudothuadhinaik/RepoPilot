# RepoPilot release readiness

Review baseline: `main` at `8645ac8fd28ba14365a0e61269bee015eb3db778`.
The audit and evaluator changes were finalized in `ffb4ed2a09a84f09915b4db3214db5614d4fa8b3`;
the CI history fix was finalized in `cbe5fbd3427f56ed1786d212a9b4816d55559f90`.
Both commits are pushed to `origin/main`.

## Verified local checks

| Check | Result | Evidence |
|---|---|---|
| Single-repository ground truth | Passed 15/15 across three recorded revisions; Recall@1 12/13, Recall@5 13/13, MRR@5 0.9423, symbol/citation accuracy 13/13, abstention 2/2 | `PYTHONPATH=src python evals/run_ground_truth.py --root .` (CI run `40941234179`) |
| Multirepository ground truth | Passed 41/41; Recall@1 29/31; Recall@5 31/31; MRR@5 0.9543; citation validity 31/31; symbol accuracy 13/13; abstention 10/10 | `PYTHONPATH=src python evals/run_multirepo_ground_truth.py --root . --output multirepo_ground_truth_results.json` |
| Focused evaluation tests | Passed 15 tests | `python -m pytest tests/test_multirepo_ground_truth.py tests/test_provider_eval.py` |
| Full Python tests | Passed 89 tests | `python -m pytest` |
| Ruff / Mypy / compilation | Passed | `python -m ruff check .`; `python -m mypy src`; `python -m compileall -q src evals tests` |
| Compose configuration | Passed through Doppler; bare validation fails closed when the token is absent | `doppler run -- docker compose config -q` |
| Frontend build and dependency audit | Passed; npm audit reported 0 vulnerabilities | `npm run build`; `npm audit --audit-level=high` from `apps/web` |
| Diff integrity | Passed | `git diff --check` |

## Snapshot and reproducibility behavior

The single-repository and multirepository benchmarks are fixed-revision by default.
The single-repository runner materializes each question's `source_revision`; the
multirepository runner materializes the RepoPilot dataset commit. The shared
`evals/multirepo_corpus.py` helper verifies that each full Git SHA exists in the
supplied repository and uses `git archive` to create isolated temporary corpora.
It does not index the worktree, `.git` directory, ground-truth datasets, external
fixture corpora, generated reports, or `docs/evaluation_audit.md`.

The external repositories are materialized from their embedded `snapshot.json`
file bundles after verifying upstream URL and commit metadata. The evaluator
reports `source_mode: git_revision` and `repo_pilot_revision_verified: true`
for the default path. A missing RepoPilot revision fails with a clear error.

To evaluate proposed, uncommitted worktree changes intentionally, use the
explicit `--use-checkout` option and treat the result as checkout-relative. On
this review tree it correctly reports 40/41 because the current source has a
different `read_safe_text` line span than the recorded baseline:

```powershell
$env:PYTHONPATH = "src"
python evals/run_multirepo_ground_truth.py --root . --use-checkout
```

## Security and evidence limitations

- The audit is AI-assisted maintainer work, not independent second-person
  review. Independent human verification of expected facts, paths, ranges, and
  unsupported cases remains required before external accuracy claims.
- The offline evaluator is lexical and source-range based. Passing it does not
  establish semantic entailment, production retrieval quality, or broad
  benchmark generalization.
- Live-provider evaluation remains unverified because valid provider credits
  were not available for this review. No live-provider success is claimed.
- No external penetration test or independent production security assessment
  was performed.

## Release blockers

The automated local checks are green. The remaining release-readiness blockers
for an externally validated claim are independent human dataset review, a
successful live-provider evaluation if provider-backed claims are required,
and any separately authorized external penetration testing. These are evidence
and review requirements, not local test failures.
