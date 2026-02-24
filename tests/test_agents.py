def test_register_agent(client):
    resp = client.post("/api/agents/register", json={
        "name": "Camera Agent",
        "description": "Near Tokyo Tower",
        "location": {"latitude": 35.6586, "longitude": 139.7454},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Camera Agent"
    assert data["api_key"].startswith("hh_")
    assert data["balance"] == 100.0
    assert data["frozen_balance"] == 0.0


def test_register_without_location(client):
    resp = client.post("/api/agents/register", json={"name": "Headless Agent"})
    assert resp.status_code == 201
    assert resp.json()["location"] is None


def test_get_me(client, registered_agent, auth_headers):
    resp = client.get("/api/agents/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == registered_agent["id"]


def test_get_me_no_key(client):
    resp = client.get("/api/agents/me")
    assert resp.status_code == 401


def test_get_me_bad_key(client):
    resp = client.get("/api/agents/me", headers={"X-API-Key": "bad_key"})
    assert resp.status_code == 401


def test_update_me(client, auth_headers):
    resp = client.patch("/api/agents/me", json={"name": "Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


def test_heartbeat(client, auth_headers):
    resp = client.post("/api/agents/heartbeat", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_agents(client, auth_headers):
    resp = client.get("/api/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["agents"]) >= 1


def test_get_agent_by_id(client, registered_agent, auth_headers):
    agent_id = registered_agent["id"]
    resp = client.get(f"/api/agents/{agent_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id


def test_get_agent_not_found(client, auth_headers):
    resp = client.get("/api/agents/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
