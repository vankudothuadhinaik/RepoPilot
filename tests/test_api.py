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


def test_api_requires_valid_bearer_token(client, auth_headers):
    assert client.get("/api/repos").status_code == 401
    assert client.get("/api/repos", headers={"Authorization": "Bearer wrong-token"}).status_code == 401
    assert client.get("/api/repos", headers=auth_headers).status_code == 200


def test_missing_repository_is_404(client, auth_headers):
    assert client.get("/api/repos/missing", headers=auth_headers).status_code == 404


def test_invalid_repository_path_is_400(client, tmp_path, auth_headers):
    response = client.post("/api/repos", json={"path": str(tmp_path)}, headers=auth_headers)
    assert response.status_code == 400
