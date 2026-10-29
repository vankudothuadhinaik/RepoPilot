"""Opt-in live-provider evaluation; emits redacted per-case metrics only."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_CITATION = re.compile(r"\[\[([^\]]+)\]\]")


class _ProviderDiagnosticCapture(logging.Handler):
    """Capture safe error categories without provider message bodies."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.codes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage().lower()
        if "provider timed out" in message:
            code = "provider_timeout"
        elif "provider returned http status" in message:
            code = "provider_http_error"
        elif "provider connection failed" in message:
            code = "provider_connection_error"
        elif "response could not be parsed" in message:
            code = "malformed_provider_response"
        elif "invalid provider configuration" in message:
            code = "invalid_provider_configuration"
        elif "rejected:" in message:
            code = "provider_response_rejected"
        else:
            return
        self.codes.append(code)

def citation_paths(answer: str) -> list[str]:
    """Return paths cited with RepoPilot's exact [[relative/path]] syntax."""
    return _CITATION.findall(answer)

def citation_is_valid(item: dict[str, Any], root: Path) -> bool:
    """Check that evidence line labels and snippets match the indexed source."""
    path, start, end = str(item.get("path", "")), item.get("start_line"), item.get("end_line")
    if (not path or not isinstance(start, int) or not isinstance(end, int) or start < 1
        or end < start or Path(path).is_absolute() or ".." in Path(path).parts or "\\" in path):
        return False
    source = root / path
    if not source.is_file():
        return False
    lines = source.read_text(encoding="utf-8").splitlines()
    if end > len(lines):
        return False
    cited: dict[int, str] = {}
    for line in str(item.get("snippet", "")).splitlines():
        number, separator, content = line.partition(": ")
        if separator and number.isdigit():
            cited[int(number)] = content
    return bool(cited) and all(
        1 <= number <= len(lines) and lines[number - 1] == content
        for number, content in cited.items()
    )

def score_case(question: dict[str, Any], response: dict[str, Any], root: Path) -> dict[str, Any]:
    """Score structural evidence properties, not semantic truth of generated prose."""
    expected_path = question.get("expected_path")
    evidence, answer = response.get("evidence") or [], response.get("answer") or ""
    cited_paths = citation_paths(answer)
    valid_evidence = [
        item for item in evidence
        if isinstance(item, dict) and citation_is_valid(item, root)
    ]
    if expected_path:
        return {
            "id": question["id"],
            "expected_path_found": any(item.get("path") == expected_path for item in evidence),
            "source_lines_valid": any(item.get("path") == expected_path for item in valid_evidence),
            "answer_has_citations": bool(cited_paths),
            "answer_citations_supported": bool(cited_paths) and set(cited_paths).issubset(
                {item.get("path") for item in evidence}),
            "abstained": bool(response.get("abstained")),
            "answer_mode": response.get("mode", "unknown"),
            "provider_answer_generated": response.get("mode") == "llm",
        }
    return {
        "id": question["id"],
        "unsupported_question_abstained": (
            bool(response.get("abstained")) and not evidence and not citation_paths(answer)
        ),
        "evidence_count": len(evidence),
        "answer_has_citations": bool(cited_paths),
        "answer_mode": response.get("mode", "unknown"),
        "provider_answer_generated": response.get("mode") == "llm",
    }

def evaluate(root: Path) -> dict[str, Any]:
    """Run the reviewed question set through the real API with a configured provider."""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return {"status": "skipped", "reason": "OPENAI_API_KEY is not configured; no provider score was produced."}
    root = root.resolve()
    dataset_path = Path(__file__).parent / "datasets" / "ground_truth.json"
    questions = json.loads(dataset_path.read_text(encoding="utf-8"))["questions"]
    with tempfile.TemporaryDirectory(prefix="repopilot-provider-eval-") as data_dir:
        os.environ["REP_PILOT_API_TOKEN"] = "provider-evaluation-local-token"
        os.environ["REP_PILOT_DATA_DIR"] = data_dir
        from fastapi.testclient import TestClient

        from repopilot.api import app
        client = TestClient(app)
        headers = {"Authorization": "Bearer provider-evaluation-local-token"}
        registration = client.post("/api/repos", json={"path": str(root)}, headers=headers)
        registration.raise_for_status()
        repo_id = registration.json()["id"]
        results, durations = [], []
        provider_logger = logging.getLogger("repopilot.llm")
        for question in questions:
            query = question.get("query") or "".join(
                chr(value) for value in question.get("query_codepoints", [])
            )
            diagnostic = _ProviderDiagnosticCapture()
            provider_logger.addHandler(diagnostic)
            started = time.perf_counter()
            try:
                response = client.post(
                    f"/api/repos/{repo_id}/ask",
                    json={"question": query, "limit": 5},
                    headers=headers,
                )
                durations.append((time.perf_counter() - started) * 1000)
                if response.status_code >= 400:
                    scored = score_case(
                        question,
                        {"answer": "", "abstained": False, "evidence": [], "mode": "error"},
                        root,
                    )
                    scored["evaluation_error"] = "api_http_error"
                    scored["http_status"] = response.status_code
                    results.append(scored)
                    continue
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                if not isinstance(payload, dict) or not all(
                    key in payload for key in ("answer", "abstained", "evidence")
                ):
                    scored = score_case(
                        question,
                        {"answer": "", "abstained": False, "evidence": [], "mode": "error"},
                        root,
                    )
                    scored["evaluation_error"] = "malformed_api_response"
                    results.append(scored)
                    continue
                scored = score_case(question, payload, root)
                if diagnostic.codes:
                    scored["provider_error"] = diagnostic.codes[-1]
                results.append(scored)
            except Exception as exc:
                # Exception messages can contain request URLs or provider response data.
                # Store only a safe class/category; never serialize the exception text.
                error_code = "request_timeout" if "timeout" in type(exc).__name__.lower() else "request_error"
                scored = score_case(
                    question,
                    {"answer": "", "abstained": False, "evidence": [], "mode": "error"},
                    root,
                )
                scored["evaluation_error"] = error_code
                results.append(scored)
            finally:
                provider_logger.removeHandler(diagnostic)
        positives = [item for item in results if "expected_path_found" in item]
        negatives = [item for item in results if "unsupported_question_abstained" in item]
        error_codes = [
            item.get("evaluation_error") or item.get("provider_error")
            for item in results
            if item.get("evaluation_error") or item.get("provider_error")
        ]
        metrics = {
            "evaluation_error_count": sum(bool(item.get("evaluation_error")) for item in results),
            "provider_error_count": sum(bool(item.get("provider_error")) for item in results),
            "timeout_count": sum(
                item.get("evaluation_error") == "request_timeout"
                or item.get("provider_error") == "provider_timeout"
                for item in results
            ),
            "malformed_response_count": sum(
                item.get("evaluation_error") == "malformed_api_response"
                or item.get("provider_error") == "malformed_provider_response"
                for item in results
            ),
            "error_categories": {code: error_codes.count(code) for code in sorted(set(error_codes))},
            "expected_path_rate": (
                round(sum(x["expected_path_found"] for x in positives) / len(positives), 4)
                if positives else None
            ),
            "valid_source_evidence_rate": (
                round(sum(x["source_lines_valid"] for x in positives) / len(positives), 4)
                if positives else None
            ),
            "answer_citation_rate": (
                round(sum(x["answer_has_citations"] for x in positives) / len(positives), 4)
                if positives else None
            ),
            "provider_answer_rate": (
                round(sum(x["provider_answer_generated"] for x in positives) / len(positives), 4)
                if positives else None
            ),
            "supported_citation_rate": (
                round(sum(x["answer_citations_supported"] for x in positives) / len(positives), 4)
                if positives else None
            ),
            "unsupported_abstention_rate": (
                round(sum(x["unsupported_question_abstained"] for x in negatives) / len(negatives), 4)
                if negatives else None
            ),
            "latency_ms_median": round(sorted(durations)[len(durations) // 2], 2) if durations else None,
        }
        passed = all(
            x.get("expected_path_found", x.get("unsupported_question_abstained", False))
            for x in results
        )
        passed = passed and all(x.get("provider_answer_generated", False) for x in positives)
        passed = passed and all(
            x.get("source_lines_valid", True) and x.get("answer_citations_supported", True)
            for x in positives
        )
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        try:
            provider_host = urlsplit(base_url).hostname
        except ValueError:
            provider_host = None
        return {
            "status": "completed", "mode": "live-provider",
            "provider": {
                "base_url_host": provider_host,
                "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or None,
                "provider_version": None,
            },
            "dataset": "evals/datasets/ground_truth.json", "question_count": len(questions),
            "positive_count": len(positives), "negative_count": len(negatives),
            "metrics": metrics, "results": results, "passed": passed,
            "limitations": [
                "The reviewed dataset is small and not representative of production use.",
                "Citation/path checks do not prove generated claims are semantically entailed by cited source.",
                "The model name and provider hostname are configuration values, not verified server-side version identifiers.",
                "Provider credentials and raw provider response bodies are never included in the report.",
                "Provider failures are categorized from redacted diagnostic codes; error messages and bodies are not recorded.",
                "Latency includes local indexing/API overhead as well as provider latency."
            ]
        }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = evaluate(args.root)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if report["status"] == "completed" and not report["passed"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
