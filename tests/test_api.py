def test_health_and_repository_workflow(client, fixture_repo):
    assert client.get("/health/live").json()["status"] == "ok"
    response = client.post("/api/repos", json={"path": str(fixture_repo)})
    assert response.status_code == 201, response.text
    repo_id = response.json()["id"]
    assert client.get(f"/api/repos/{repo_id}/symbols").status_code == 200
    assert client.post(f"/api/repos/{repo_id}/search", json={"question": "greet"}).json()["result_count"] >= 1
    ask = client.post(f"/api/repos/{repo_id}/ask", json={"question": "greet"}).json()
    assert ask["evidence"]
    assert client.post(f"/api/repos/{repo_id}/memories", json={
        "type": "note", "summary": "Example memory", "evidence": ["README.md"]
    }).status_code == 201


def test_missing_repository_is_404(client):
    assert client.get("/api/repos/missing").status_code == 404


def test_invalid_repository_path_is_400(client, tmp_path):
    response = client.post("/api/repos", json={"path": str(tmp_path)})
    assert response.status_code == 400
