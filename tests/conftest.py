import pytest
from fastapi.testclient import TestClient

from repopilot import api
from repopilot.store import Store


@pytest.fixture
def fixture_repo(tmp_path):
    root = tmp_path / "sample"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "README.md").write_text("# Sample\nA tiny test repository.\n", encoding="utf-8")
    (root / "app.py").write_text(
        "def greet(name: str) -> str:\n    return f'hello {name}'\n\nclass Service:\n    pass\n",
        encoding="utf-8",
    )
    (root / "settings.py").write_text("import app\nTOKEN = 'not-a-real-secret'\n", encoding="utf-8")
    (root / ".env").write_text("API_KEY=should-not-index\n", encoding="utf-8")
    (root / "ignored.bin").write_bytes(b"\x00\x01")
    return root


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite3")


@pytest.fixture
def client(tmp_path, monkeypatch):
    api.store = Store(tmp_path / "api.sqlite3")
    return TestClient(api.app)
