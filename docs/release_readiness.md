# RepoPilot release readiness

## Current repository status

- README and free-provider setup documentation updated on `main`.
- Latest documentation commit: [6a579241eb1d7024637337639a9fbea91233e558](https://github.com/vankudothuadhinaik/RepoPilot/commit/6a579241eb1d7024637337639a9fbea91233e558).
- Free-provider CI support merged in [PR #48](https://github.com/vankudothuadhinaik/RepoPilot/pull/48).
- Earlier verified main code snapshot: [`9cc356575931a129df64928ca88b1b36c52d4e74`](https://github.com/vankudothuadhinaik/RepoPilot/commit/9cc356575931a129df64928ca88b1b36c52d4e74), with [CI](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358423) and [CodeQL](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358478) passed.
- Merged follow-up PRs: [#45](https://github.com/vankudothuadhinaik/RepoPilot/pull/45), [#46](https://github.com/vankudothuadhinaik/RepoPilot/pull/46), [#47](https://github.com/vankudothuadhinaik/RepoPilot/pull/47), and [#48](https://github.com/vankudothuadhinaik/RepoPilot/pull/48).

## Verified automated evaluation

- Single-repository ground truth: 15/15 across three recorded Git revisions.
- Multirepository ground truth: 41/41.
- Earlier reported single-repository metrics: Recall@1 12/13, Recall@5 13/13, MRR@5 0.9423, symbol/citation accuracy 13/13, unsupported abstention 2/2.
- Earlier reported multirepository metrics: Recall@1 29/31, Recall@5 31/31, MRR@5 0.9543, citation validity 31/31, symbol accuracy 13/13, unsupported abstention 10/10.

## Live-provider evaluation

The optional provider check is manual-only. The workflow supports a free-tier Gemini API key through the `GEMINI_API_KEY` repository secret, and continues to support existing OpenAI-compatible credentials. Follow [the provider evaluation guide](live-provider-evaluation.md). Free-tier eligibility and quota are provider-controlled; do not enable billing for this project. A successful live-provider evaluation must be evidenced by its actual run report, not inferred from unrelated green CI jobs.

## Evidence limitations

The ground-truth cases are curated maintainer-authored checks. Independent second-person review of all 56 cases remains separate from automated CI. The lexical/source-range evaluator does not prove semantic entailment or production retrieval quality. No external penetration test or independent production security assessment is claimed.
