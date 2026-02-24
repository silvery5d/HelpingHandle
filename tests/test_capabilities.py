def test_create_capability(client, auth_headers):
    resp = client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "HD Camera 4K",
        "device_info": "Sony IMX586",
        "metadata": {"resolution": "3840x2160"},
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "sensor"
    assert data["status"] == "online"
    assert data["metadata"]["resolution"] == "3840x2160"


def test_list_capabilities(client, auth_headers):
    client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "Camera",
    }, headers=auth_headers)
    client.post("/api/capabilities", json={
        "type": "actuator",
        "description": "Robotic arm",
    }, headers=auth_headers)

    resp = client.get("/api/capabilities", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    resp = client.get("/api/capabilities?type=sensor", headers=auth_headers)
    assert resp.json()["total"] == 1


def test_update_capability(client, auth_headers):
    resp = client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "Camera",
    }, headers=auth_headers)
    cap_id = resp.json()["id"]

    resp = client.patch(f"/api/capabilities/{cap_id}", json={
        "status": "offline",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "offline"


def test_delete_capability(client, auth_headers):
    resp = client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "Camera",
    }, headers=auth_headers)
    cap_id = resp.json()["id"]

    resp = client.delete(f"/api/capabilities/{cap_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/capabilities/{cap_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_cannot_modify_others_capability(client, auth_headers):
    resp = client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "Camera",
    }, headers=auth_headers)
    cap_id = resp.json()["id"]

    resp2 = client.post("/api/agents/register", json={"name": "Other"})
    other_key = resp2.json()["api_key"]

    resp = client.patch(f"/api/capabilities/{cap_id}", json={
        "description": "Hacked",
    }, headers={"X-API-Key": other_key})
    assert resp.status_code == 403
