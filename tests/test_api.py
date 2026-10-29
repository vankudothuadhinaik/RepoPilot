def test_health_and_repository_workflow(client, fixture_repo, auth_headers):
    assert client.get("/health/live").json()["status"] == "ok"
    assert client.get("/health/ready").json()["status"] == "ready"
    response = client.post("/api/repos", json={"path": str(fixture_repo)}, headers=auth_headers)
    assert response.status_code == 201, response.text
    repo_id = response.json()["id"]
    assert client.get(f"/api/repos/{repo_id}/symbols", headers=auth_headers).status_code == 200
    assert client.post(f"/api/repos/{repo_id}/search", json={"question": "greet"}, headers=auth_headers).json()["result_count"] >= 1
    ask = client.post(f"/api/repos/{repo_id}/ask", json={"question": "greet"}, headers=auth_headers).json()
    assert ask["evidence"]
    assert client.post(
        f"/api/repos/{repo_id}/memories",
        json={"type": "note", "summary": "Example memory", "evidence": ["README.md"]},
        headers=auth_headers,
    ).status_code == 201


def test_ask_returns_line_addressable_evidence(client, fixture_repo, auth_headers):
    response = client.post("/api/repos", json={"path": str(fixture_repo)}, headers=auth_headers)
    repo_id = response.json()["id"]

    ask = client.post(
        f"/api/repos/{repo_id}/ask",
        json={"question": "greet", "limit": 5},
        headers=auth_headers,
    )

    assert ask.status_code == 200
    body = ask.json()
    assert body["abstained"] is False
    citation = next(item for item in body["evidence"] if item["path"] == "app.py")
    assert citation["start_line"] <= 1 <= citation["end_line"]
    assert "1: def greet" in citation["snippet"]
    assert citation["sha256"]


def test_missing_repository_is_404(client, auth_headers):
    assert client.get("/api/repos/missing", headers=auth_headers).status_code == 404


def test_invalid_repository_path_is_400(client, tmp_path, auth_headers):
    response = client.post("/api/repos", json={"path": str(tmp_path)}, headers=auth_headers)
    assert response.status_code == 400



def test_api_token_guard_protects_api_but_not_health(client, monkeypatch):
    monkeypatch.setenv("REP_PILOT_API_TOKEN", "test-secret-token")
    assert client.get("/health/live").status_code == 200
    assert client.get("/api/repos").status_code == 401
    assert client.get("/api/repos", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = client.get("/api/repos", headers={"Authorization": "Bearer test-secret-token"})
    assert response.status_code == 200



def test_ask_empty_file_and_no_keyword_match_have_bounded_citations(client, fixture_repo, auth_headers):
    (fixture_repo / "empty.py").write_text("", encoding="utf-8")
    (fixture_repo / "unrelated.py").write_text(
        "def unrelated_function():\n    return 'alpha beta gamma'\n", encoding="utf-8"
    )
    registered = client.post("/api/repos", json={"path": str(fixture_repo)}, headers=auth_headers)
    repo_id = registered.json()["id"]

    response = client.post(
        f"/api/repos/{repo_id}/ask",
        json={"question": "completely absent concept", "limit": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    for citation in body["evidence"]:
        assert citation["start_line"] >= 1
        assert citation["end_line"] >= citation["start_line"]
        assert len(citation["snippet"].splitlines()) <= 12



def test_every_api_route_requires_authentication(client, fixture_repo):
    repo_response = client.post(
        "/api/repos", json={"path": str(fixture_repo)},
        headers={"Authorization": "Bearer test-api-token"},
    )
    repo_id = repo_response.json()["id"]
    memory_response = client.post(
        f"/api/repos/{repo_id}/memories",
        json={"type": "note", "summary": "temporary"},
        headers={"Authorization": "Bearer test-api-token"},
    )
    memory_id = memory_response.json()["id"]
    requests = [
        ("GET", "/api/repos", None),
        ("POST", "/api/repos", {"path": str(fixture_repo)}),
        ("GET", f"/api/repos/{repo_id}", None),
        ("POST", f"/api/repos/{repo_id}/index", None),
        ("POST", f"/api/repos/{repo_id}/search", {"question": "greet"}),
        ("POST", f"/api/repos/{repo_id}/ask", {"question": "greet"}),
        ("GET", f"/api/repos/{repo_id}/symbols", None),
        ("GET", f"/api/repos/{repo_id}/graph", None),
        ("GET", f"/api/repos/{repo_id}/files/README.md", None),
        ("GET", f"/api/repos/{repo_id}/memories", None),
        ("POST", f"/api/repos/{repo_id}/memories", {"type": "note", "summary": "x"}),
        ("PATCH", f"/api/memories/{memory_id}", {"status": "verified"}),
        ("DELETE", f"/api/memories/{memory_id}", None),
        ("DELETE", f"/api/repos/{repo_id}", None),
    ]
    for method, url, body in requests:
        response = client.request(method, url, json=body)
        assert response.status_code == 401, f"{method} {url} returned {response.status_code}"



def test_memory_status_and_search_filters_are_validated(client, fixture_repo, auth_headers):
    registered = client.post("/api/repos", json={"path": str(fixture_repo)}, headers=auth_headers)
    repo_id = registered.json()["id"]
    invalid_memory = client.post(
        f"/api/repos/{repo_id}/memories",
        json={"type": "note", "summary": "bad status", "status": "unknown"},
        headers=auth_headers,
    )
    assert invalid_memory.status_code == 422
    invalid_update = client.patch(
        "/api/memories/not-a-real-id",
        json={"status": "unknown"},
        headers=auth_headers,
    )
    assert invalid_update.status_code == 422
    invalid_language = client.post(
        f"/api/repos/{repo_id}/search",
        json={"question": "greet", "language": "../"},
        headers=auth_headers,
    )
    assert invalid_language.status_code == 422
