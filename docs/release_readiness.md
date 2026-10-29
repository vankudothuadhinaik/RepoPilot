# RepoPilot release readiness

## Current repository status

- The current main snapshot before this documentation update is [`c9dfd71e88cd88b420bb48e1819bf34fa337b5fd`](https://github.com/vankudothuadhinaik/RepoPilot/commit/c9dfd71e88cd88b420bb48e1819bf34fa337b5fd).
- [CI run #343](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40949635764) and [CodeQL](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40949635579) both completed successfully on that exact snapshot.
- Free-provider CI support is merged in [PR #48](https://github.com/vankudothuadhinaik/RepoPilot/pull/48). Related merged work: [PR #45](https://github.com/vankudothuadhinaik/RepoPilot/pull/45), [PR #46](https://github.com/vankudothuadhinaik/RepoPilot/pull/46), and [PR #47](https://github.com/vankudothuadhinaik/RepoPilot/pull/47).

## Verified automated evaluation

- Single-repository ground truth: 15/15 cases.
- Multirepository ground truth: 41/41 cases.
- Recorded single-repository metrics: Recall@1 12/13, Recall@5 13/13, MRR@5 0.9423, symbol/citation checks 13/13, unsupported abstention 2/2.
- Recorded multirepository metrics: Recall@1 29/31, Recall@5 31/31, MRR@5 0.9543, citation validity 31/31, symbol accuracy 13/13, unsupported abstention 10/10.

## Live-provider evaluation

- Manual workflow run [#40947962027](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40947962027) completed successfully and published the artifact `repopilot-live-provider-evaluation-841ff7a50511600f382d1f27ccebea13b8dd5f43-py3.11`.
- The workflow is configured to continue after a provider-evaluation command error, so a green workflow and artifact existence alone do **not** prove the evaluation passed. Inspect the artifact/report summary and record `status: completed` with `passed: true` before claiming a live-provider pass.
- The workflow supports an eligible free-tier Gemini API key through the `GEMINI_API_KEY` repository secret and remains compatible with OpenAI-compatible providers. Follow [the provider evaluation guide](live-provider-evaluation.md). Provider quotas and model availability are provider-controlled; do not enable paid billing.

## Remaining independent checks and limitations

- Independent second-person review of all 56 curated cases (15 single-repository and 41 multirepository) remains outstanding unless separately completed and recorded.
- These maintainer-authored checks and lexical/source-range metrics do not prove semantic entailment or production retrieval quality.
- No external penetration test or independent production security assessment is claimed.
