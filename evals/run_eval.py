"""Small deterministic retrieval smoke evaluation; not an LLM answer-quality benchmark."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from repopilot.indexer import index_repository
from repopilot.store import Store


def main() -> None:
    dataset = json.loads((Path(__file__).parent / "datasets/smoke.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "fixture"
        root.mkdir()
        (root / ".git").mkdir()
        (root / "app.py").write_text(
            "def greet(name):\n    return name\nclass Service:\n    pass\n", encoding="utf-8"
        )
        store = Store(Path(temp) / "eval.sqlite3")
        repo = store.index(index_repository(root))
        passed = 0
        details = []
        for case in dataset:
            if case["expected_path"] is None:
                found = store.search(repo["id"], "this_token_should_not_exist_12345")
                ok = len(found) == 0
            else:
                found = store.search(repo["id"], case["query"], limit=10)
                ok = any(item["path"] == case["expected_path"] for item in found)
            passed += int(ok)
            details.append({"id": case["id"], "passed": ok})
        print(json.dumps({"passed": passed, "total": len(dataset), "results": details}, indent=2))
        if passed != len(dataset):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
