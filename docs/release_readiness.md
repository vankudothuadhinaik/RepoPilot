# RepoPilot release readiness

## Current verified main snapshot

- Main commit: [`9cc356575931a129df64928ca88b1b36c52d4e74`](https://github.com/vankudothuadhinaik/RepoPilot/commit/9cc356575931a129df64928ca88b1b36c52d4e74)
- [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358423): passed.
- [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358478): passed.
- Merged follow-ups: [PR #45](https://github.com/vankudothuadhinaik/RepoPilot/pull/45), [PR #46](https://github.com/vankudothuadhinaik/RepoPilot/pull/46), [PR #47](https://github.com/vankudothuadhinaik/RepoPilot/pull/47).

## Verified automated evaluation

| Check | Result | Evidence |
|---|---|---|
| Single-repository ground truth | Passed 15/15 across three recorded Git revisions; Recall@1 12/13, Recall@5 13/13, MRR@5 0.9423, symbol/citation accuracy 13/13, abstention 2/2 | Ground-truth CI run and evaluation artifacts |
| Multirepository ground truth | Passed 41/41; Recall@1 29/31; Recall@5 31/31; MRR@5 0.9543; citation validity 31/31; symbol accuracy 13/13; abstention 10/10 | Ground-truth evaluation artifacts |
| Main CI | Passed | [CI run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358423) |
| CodeQL | Passed | [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358478) |
| Live provider evaluation | Not passed / not rerun after made manual-only | See limitations below |

## Snapshot and reproducibility behavior

The single-repository and multirepository benchmarks use fixed Git revisions by default. The single-repository runner materializes each question's `source_revision`; the multirepository runner materializes the RepoPilot dataset commit. The shared `evals/multirepo_corpus.py` helper verifies each full Git SHA and uses `git archive` to create isolated temporary corpora. Ground-truth datasets, audit reports, external corpora, and generated evaluation artifacts are excluded from the indexed source.

External repositories are materialized from embedded `snapshot.json` bundles after verifying upstream URL and commit metadata. The evaluator reports `source_mode: git_revision` and `repo_pilot_revision_verified: true` for the default path. A missing RepoPilot revision fails with a clear error. To evaluate uncommitted worktree changes intentionally, use the explicit `--use-checkout` option and label the result checkout-relative.

## Security and evidence limitations

- The dataset audit is AI-assisted maintainer work, not independent second-person review. Independent human verification of expected facts, paths, ranges, and unsupported cases remains required before external accuracy claims.
- The offline evaluator is lexical and source-range based. Passing it does not establish semantic entailment, production retrieval quality, or broad benchmark generalization.
- Live-provider evaluation is manual-only to avoid routine provider credit spending. An earlier run failed with 13 HTTP errors across 13 positive cases; an earlier provider response identified `429 credit_balance_exhausted`. A successful live-provider run has not been verified. Restore valid provider credits and verify the GitHub Actions secret `OPENAI_API_KEY` without exposing it, then manually run CI on `main`.
- No external penetration test or independent production security assessment was performed.

## Release status

**Automated code and static-analysis gates are green on the verified main commit.** Remaining external evidence tasks are independent human dataset review, successful live-provider evaluation if provider-backed claims are required, and authorized external penetration testing if an external security-assurance claim is required. These are explicitly disclosed validation gaps, not claims of completed work.
