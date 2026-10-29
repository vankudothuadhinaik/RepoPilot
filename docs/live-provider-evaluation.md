# Live provider evaluation

RepoPilot's live-provider evaluator supports OpenAI-compatible APIs through three environment variables. **No paid API is required.** Use a provider's $0 free tier and stay within its published limits.

## Recommended: Google Gemini API free tier

Google documents an OpenAI-compatible endpoint and a free tier for eligible models. See the [official compatibility guide](https://ai.google.dev/gemini-api/docs/openai) and [official pricing page](https://ai.google.dev/gemini-api/docs/pricing). Free-tier availability and quotas depend on model and account/project eligibility; do not enable billing or upgrade to a paid tier for this evaluation.

1. Open [Google AI Studio](https://aistudio.google.com/apikey) and create an API key for an eligible free-tier project. If it asks you to enable paid billing, stop and use another free provider or local testing instead.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions** and add/update these repository secrets:
   - OPENAI_API_KEY: your Gemini API key (the variable name is legacy; the value can be a Gemini key).
   - OPENAI_BASE_URL: https://generativelanguage.googleapis.com/v1beta/openai/
   - OPENAI_MODEL: gemini-3.8-flash (confirm that this model is available on your free tier; otherwise choose an available free model listed by AI Studio).
3. Open **Actions → CI → Run workflow**, choose main, and run it. The live-provider evaluation only runs on manual dispatch and is intentionally optional.
4. Open the run summary and download the artifact named repopilot-live-provider-evaluation-.... A successful result must show status completed and passed: true; a skipped result is not a pass. If the provider rejects the model or quota, select a currently available free model or wait for quota reset. Do not add billing or a payment method just to pass this check.

Never put the key in source code, workflow YAML, issue comments, logs, or this report. GitHub Actions secrets keep it out of the repository files.

## Other free options

An OpenAI-compatible free-tier endpoint can also be configured using the same variables. Check current limits and model availability directly with the provider before use; free-tier availability changes. Do not use a paid endpoint, trial balance, or a provider that requires billing to meet this project's $0 constraint.

## Run locally

Run: PYTHONPATH=src python evals/run_provider_eval.py --root . --output provider-evaluation.json

Without OPENAI_API_KEY, the command emits JSON with status skipped and does not claim a score. It never includes the key in the report. The command calls the real RepoPilot API against the reviewed question set and records path retrieval, source-line validity, citation structure, unsupported-question abstention, and latency. It returns a nonzero exit code when a completed run fails structural checks.

## Interpretation limits

The single-repository baseline and multi-repository source-grounded dataset are small, curated evaluation sets, not representative model benchmarks. The multi-repository dataset has 31 positive cases and 10 unsupported cases; independent second-person review is still pending. Do not treat these outputs as a general model benchmark or production accuracy estimate. Automated citation checks show whether paths and displayed source lines are consistent; they do not prove every natural-language claim is entailed by its cited source.

Do not commit provider keys, raw prompts containing private source code, or provider responses that may expose repository content. Review the report before sharing it. External penetration testing is outside this evaluator's scope.

Provider failures are represented by redacted categories such as provider_timeout, provider_http_error, provider_connection_error, malformed_provider_response, and provider_response_rejected. Reports exclude exception messages, response bodies, and API keys. A provider hostname and configured model name are configuration metadata, not proof of the exact model build serving the request.

The versioned question set records source revisions, expected facts, symbols/ranges, and source anchors. The provider report includes the dataset SHA-256, configured model, provider hostname, runtime, per-case expected-range coverage, symbol-range checks, exact-quote support against cited evidence, and aggregate denominators. These are structural checks, not semantic adjudication. Independent review of the dataset remains required for external accuracy claims.
