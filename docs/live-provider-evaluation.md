# Live provider evaluation

The offline synthetic and reviewed ground-truth evaluations remain the deterministic CI baseline. To run the optional provider check locally, configure an OpenAI-compatible provider using RepoPilot's existing environment variables (OPENAI_API_KEY, optional OPENAI_BASE_URL, and optional OPENAI_MODEL) and run:

```bash
PYTHONPATH=src python evals/run_provider_eval.py --root . --output provider-evaluation.json
```

Without OPENAI_API_KEY, the command emits JSON with status "skipped" and does not claim a score. The key is never included in the report. The command calls the real RepoPilot API against the reviewed question set and records path retrieval, source-line validity, citation structure, unsupported-question abstention, and latency. It returns a nonzero exit code when a completed run fails structural checks.

## Interpretation limits

The single-repository baseline and the multi-repository source-grounded dataset are small, curated evaluation sets, not representative model benchmarks. The multi-repository dataset currently has 31 positive cases and 10 unsupported cases, but its independent second-person review is still pending. Do not treat either output as a general model benchmark or production accuracy estimate. Automated citation checks show whether paths and displayed source lines are consistent; they do not prove that every natural-language claim is entailed by its cited source. Semantic claim correctness requires an independently reviewed answer rubric and human or carefully validated claim-level adjudication.

Do not commit provider keys, raw prompts containing private source code, or provider responses that may expose repository content. Review the report before sharing it. External penetration testing is outside this evaluator's scope.
