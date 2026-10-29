# Final validation report

## Scope and reproducibility

This report records the validation run performed from `C:\Users\vanku\Downloads\RepoPilot` on Windows PowerShell against source commit `d401ddbff36a363ad12b9caf2fbeba4eea77e358`, before the evaluation/documentation changes in this handoff. No external penetration test, hosted deployment, or live LLM-provider evaluation was performed.

Environment observed during the run:

- Windows PowerShell workspace.
- Python, Docker Desktop, Doppler CLI, Node.js/npm, and the existing local Compose service available.
- Four local repositories were inspected without modifying their working trees: RepoPilot, DataPulse-Analytics, healthstream-etl, and low_latency_matching_engine.

## Commands and results

```powershell
python evals/run_eval.py
python evals/run_ground_truth.py --root .
python evals/run_multi_repo.py --repo "RepoPilot=C:\Users\vanku\Downloads\RepoPilot" --repo "DataPulse=C:\Users\vanku\Downloads\Projects\DataPulse-Analytics" --repo "Healthstream=C:\Users\vanku\Downloads\healthstream-etl" --repo "Matching=C:\Users\vanku\Downloads\Projects\low_latency_matching_engine\low_latency_matching_engine" --case "RepoPilot|authorization middleware|src/repopilot/api.py" --case "DataPulse|health|backend/app/main.py" --case "Healthstream|pipeline|src/pipeline.py" --case "Matching|residual quantity|src/MatchingEngine.cpp"
python -m pytest
python -m ruff check .
python -m mypy src/repopilot
python -m compileall -q src
cd apps/web; npm ci; npm audit --audit-level=moderate; npm run build
cd ../..
docker compose config --quiet
doppler run -- docker compose up --build -d
```

Results:

- Existing synthetic evaluation: passed, 50/50 cases; Recall@5 1.0, Recall@10 1.0, MRR@10 1.0, abstention accuracy 1.0.
- Reviewed ground-truth evaluation: passed; 3 positive and 1 negative question, Recall@5 1.0, MRR@5 0.5, symbol accuracy 1.0, citation accuracy 1.0, unsupported-abstention rate 1.0.
- Four-repository indexing spot check: all four indexed with zero scanner errors; each selected expected file appeared in the first five results. The run indexed 52/116 files/symbols for RepoPilot, 18/10 for DataPulse-Analytics, 12/15 for healthstream-etl, and 15/0 for low_latency_matching_engine.
- Python tests, Ruff, Mypy, compilation, frontend clean install/audit/build, and Compose validation passed.
- Docker readiness returned `200`, unauthenticated `/api/repos` returned `401`, and a Doppler-authenticated request returned `200` without exposing the token.
- Missing and empty `REP_PILOT_API_TOKEN` both caused Compose configuration to exit nonzero.
- A repository registered at container-visible `/app` remained present after a Compose restart. A Windows host path correctly returned `400` because the default Compose file does not mount host source directories.
- Container inspection confirmed loopback-only host binding, non-root `appuser`, read-only root filesystem, dropped capabilities, `no-new-privileges`, tmpfs, and persistent `/data` volume.

The synthetic and ground-truth scores are bounded validation signals, not production accuracy or security assurance. CI and CodeQL remain the authoritative remote workflow checks after the handoff commit.
