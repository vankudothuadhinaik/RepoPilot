# Evaluation

Run the deterministic smoke check and synthetic retrieval benchmark:

```bash
python evals/run_eval.py
```

The run combines:
- A three-case wiring smoke test.
- A 50-case synthetic retrieval benchmark spanning three fixture repositories and 15 hand-authored source files: 45 positive path-retrieval queries and five negative/abstention queries.

The benchmark reports Recall@5, Recall@10, MRR@10, and abstention accuracy, plus per-query expected path and rank. CI uploads the full JSON report as a commit-specific artifact named `repopilot-retrieval-benchmark-<sha>` for 30 days.

**Interpretation boundary:** the fixture content and queries are intentionally curated to verify deterministic lexical retrieval behavior. This is not a representative real-world corpus, a semantic retrieval benchmark, an LLM answer-quality evaluation, or a security certification. Do not present these metrics as production accuracy.

## Reviewed ground-truth check

Run the API-level source-grounded check from the repository root:

```bash
python evals/run_ground_truth.py --root .
```

The question set is [`evals/datasets/ground_truth.json`](../evals/datasets/ground_truth.json). Positive questions specify an expected file, Python symbol, and independently checked source range. The negative question uses an encoded query so the question text itself is not indexed as evidence. The evaluator registers the selected repository through the real API, then checks:

- **Recall@5:** positive questions whose expected file appears in the first five search results divided by all positive questions.
- **MRR@5:** the mean reciprocal rank of the expected file when it appears in the first five results; a miss contributes zero.
- **Symbol accuracy:** positive questions whose expected symbol and exact start/end range match the indexed symbol record divided by all positive questions.
- **Citation accuracy:** positive questions with an expected file, overlapping source range, valid line bounds, and snippet lines matching the source file exactly divided by all positive questions.
- **Unsupported-abstention rate:** negative questions returning `abstained: true` with no evidence divided by all negative questions. This is not a claim that every unsupported question is detected.

This check measures retrieval and citation mechanics for the reviewed corpus only. It does not evaluate generated answer truthfulness with a live model provider. `OPENAI_API_KEY` is intentionally not required.

## Real local repositories

For reproducible top-five spot checks against repositories that are actually present on a machine, pass explicit paths and expected files to the multi-repository runner. The command below is an example for the Windows validation workspace; replace paths only with repositories you have permission to inspect:

```powershell
python evals/run_multi_repo.py `
  --repo "RepoPilot=C:\Users\vanku\Downloads\RepoPilot" `
  --repo "DataPulse=C:\Users\vanku\Downloads\Projects\DataPulse-Analytics" `
  --repo "Healthstream=C:\Users\vanku\Downloads\healthstream-etl" `
  --repo "Matching=C:\Users\vanku\Downloads\Projects\low_latency_matching_engine\low_latency_matching_engine" `
  --case "RepoPilot|authorization middleware|src/repopilot/api.py" `
  --case "DataPulse|health|backend/app/main.py" `
  --case "Healthstream|pipeline|src/pipeline.py" `
  --case "Matching|residual quantity|src/MatchingEngine.cpp"
```

This is a top-five spot check, not a recall estimate: the expected files are supplied by the reviewer, and the runner reports the repository commit, indexed file/symbol counts, scanner errors, and each observed rank. Do not report a repository as tested unless its path and output are retained.

Before a release claim, add a reviewed and independently authored question set from multiple real-but-permitted repositories and measure:
- Recall@k and MRR for evidence retrieval.
- Citation/path correctness and citation line validity.
- Unsupported claim and abstention rates for each configured LLM provider.
- Index duration, query latency, and memory use on small/medium/large repositories.
- Incremental re-index correctness, including parser-version invalidation.
- Secret exclusion and malicious repository instruction handling.
- Comparison of keyword retrieval against any later hybrid or embedding implementation.

Publish the raw results and methodology, including corpus provenance and limitations. Never invent or extrapolate a score from the synthetic benchmark.
