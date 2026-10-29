# Validation report

## Current remote status

- README updated with current project status and a link to the no-cost provider setup.
- Free Gemini-compatible provider support merged in [PR #48](https://github.com/vankudothuadhinaik/RepoPilot/pull/48).
- Current documentation updates are on `main`; see [latest commit](https://github.com/vankudothuadhinaik/RepoPilot/commits/main/).
- Previously verified code snapshot: [`9cc356575931a129df64928ca88b1b36c52d4e74`](https://github.com/vankudothuadhinaik/RepoPilot/commit/9cc356575931a129df64928ca88b1b36c52d4e74).
- [CI](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358423) and [CodeQL](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40942358478) passed on that code snapshot.

## Offline source-grounded evaluation

| Metric | Single repository | Multirepository |
|---|---:|---:|
| Cases passed | 15/15 | 41/41 |
| Recall@1 | 12/13 | 29/31 |
| Recall@5 | 13/13 | 31/31 |
| MRR@5 | 0.9423 | 0.9543 |
| Citation/symbol checks | 13/13 | 100% for applicable cases |
| Unsupported abstention | 2/2 | 10/10 |

The evaluation materializes pinned Git revisions by default. The multirepository corpus excludes ground-truth data, audit reports, external fixture corpora, and generated reports from indexed source. Checkout-relative evaluation requires explicit `--use-checkout`.

These are curated maintainer-authored cases. They do not establish semantic entailment or production retrieval accuracy. Independent second-person review of the 56 cases remains a separate quality-assurance step.

## Free live-provider evaluation

The workflow supports an eligible free-tier Gemini API key via the `GEMINI_API_KEY` GitHub Actions secret and remains compatible with existing OpenAI-compatible providers. See [the setup guide](live-provider-evaluation.md). It is manual-only and should be run only after a free-tier key is configured. Provider quotas and model availability depend on the provider account. Do not enable paid billing for this project. A green ordinary CI run is not evidence that the live-provider evaluation itself passed; use the run summary and redacted artifact.

## Security and deployment evidence

Previously recorded local/staging checks included readiness 200, unauthorized requests 401, authenticated requests 200, restart recovery, and hardened container settings. These do not constitute external security certification. No external penetration test or independent production security assessment is claimed.
