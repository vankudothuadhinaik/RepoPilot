# Validation report

## Current remote status

- README updated with current project status and a link to the no-cost provider setup.
- Free Gemini-compatible provider support merged in [PR #48](https://github.com/vankudothuadhinaik/RepoPilot/pull/48).
- Current documentation updates are on `main`; see [latest commit](https://github.com/vankudothuadhinaik/RepoPilot/commits/main/).
- Latest code-and-documentation snapshot: [`9898ccc03724c119e508567ee1ac8eaee4543ea8`](https://github.com/vankudothuadhinaik/RepoPilot/commit/9898ccc03724c119e508567ee1ac8eaee4543ea8).
- [CI run #342](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40948803823) passed on that exact commit, including Python 3.11/3.12 tests, Windows security checks, frontend build, Docker build, and optional MCP import.
- [CodeQL run](https://github.com/vankudothuadhinaik/RepoPilot/actions/runs/40948803798) is linked for the same snapshot; see the run page for its conclusion.

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
