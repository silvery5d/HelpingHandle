def test_update_and_get_statuses(client, auth_headers):
    resp = client.put("/api/status", json={
        "statuses": [
            {"key": "can_fly", "value": True},
            {"key": "battery_level", "value": 0.85},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["statuses"]) == 2
    keys = {s["key"] for s in data["statuses"]}
    assert keys == {"can_fly", "battery_level"}

    resp = client.get("/api/status", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["statuses"]) == 2


def test_upsert_overwrites(client, auth_headers):
    client.put("/api/status", json={
        "statuses": [{"key": "battery_level", "value": 0.9}],
    }, headers=auth_headers)
    client.put("/api/status", json={
        "statuses": [{"key": "battery_level", "value": 0.5}],
    }, headers=auth_headers)

    resp = client.get("/api/status", headers=auth_headers)
    statuses = {s["key"]: s["value"] for s in resp.json()["statuses"]}
    assert statuses["battery_level"] == 0.5


def test_get_other_agent_statuses(client, registered_agent, auth_headers):
    client.put("/api/status", json={
        "statuses": [{"key": "can_move", "value": True}],
    }, headers=auth_headers)

    # Register a second agent to query the first
    resp2 = client.post("/api/agents/register", json={"name": "Agent B"})
    key2 = resp2.json()["api_key"]

    resp = client.get(f"/api/status/{registered_agent['id']}", headers={"X-API-Key": key2})
    assert resp.status_code == 200
    assert len(resp.json()["statuses"]) == 1
