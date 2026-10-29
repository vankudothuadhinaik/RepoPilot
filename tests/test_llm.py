import json

from repopilot.llm import generate_grounded_answer


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_llm_is_opt_in(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}]) is None


def test_llm_accepts_known_path_citations(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "repopilot.llm.urlopen",
        lambda *args, **kwargs: FakeResponse({
            "choices": [{"message": {"content": "Auth is implemented here [[src/auth.py]]."}}]
        }),
    )
    answer = generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}])
    assert answer == "Auth is implemented here [[src/auth.py]]."


def test_llm_rejects_unknown_path_citations(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "repopilot.llm.urlopen",
        lambda *args, **kwargs: FakeResponse({
            "choices": [{"message": {"content": "Auth is here [[src/secret.py]]."}}]
        }),
    )
    assert generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}]) is None



def test_llm_rejects_invalid_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "file:///etc")
    assert generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}]) is None


def test_llm_rejects_malformed_citation_tokens(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "repopilot.llm.urlopen",
        lambda *args, **kwargs: FakeResponse({
            "choices": [{"message": {"content": "Auth is here [[src/auth.py]."}}]
        }),
    )
    assert generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}]) is None


def test_llm_rejects_oversized_provider_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class OversizedResponse(FakeResponse):
        def read(self, amount=-1):
            return b"x" * (amount + 1 if amount > 0 else 300_000)

    monkeypatch.setattr("repopilot.llm.urlopen", lambda *args, **kwargs: OversizedResponse({}))
    assert generate_grounded_answer("Where is auth?", [{"path": "src/auth.py", "snippet": "auth"}]) is None
