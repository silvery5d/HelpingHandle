from unittest.mock import MagicMock, patch


def _register_two_agents(client):
    """Register agent A (requester) and agent B (executor)."""
    resp_a = client.post("/api/agents/register", json={
        "name": "Requester",
        "location": {"latitude": 35.6586, "longitude": 139.7454},
    })
    a = resp_a.json()

    resp_b = client.post("/api/agents/register", json={
        "name": "Executor",
        "location": {"latitude": 35.66, "longitude": 139.75},
    })
    b = resp_b.json()

    # Give executor a capability
    client.post("/api/capabilities", json={
        "type": "sensor",
        "description": "HD Camera",
    }, headers={"X-API-Key": b["api_key"]})

    return a, b


def test_create_demand_with_bounty(client):
    a, _ = _register_two_agents(client)
    headers = {"X-API-Key": a["api_key"]}

    resp = client.post("/api/demands", json={
        "description": "Need a camera near Tokyo Tower",
        "bounty_amount": 30.0,
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["bounty_amount"] == 30.0
    assert data["status"] == "open"

    # Check balance was frozen
    wallet = client.get("/api/wallet", headers=headers).json()
    assert wallet["balance"] == 70.0
    assert wallet["frozen_balance"] == 30.0


def test_create_demand_insufficient_balance(client):
    a, _ = _register_two_agents(client)
    headers = {"X-API-Key": a["api_key"]}

    resp = client.post("/api/demands", json={
        "description": "Expensive task",
        "bounty_amount": 999.0,
    }, headers=headers)
    assert resp.status_code == 400


def test_demand_complete_enters_verifying(client):
    """Test: complete with bounty enters 'verifying' status (requires multi-agent verification)."""
    a, b = _register_two_agents(client)
    ha = {"X-API-Key": a["api_key"]}

    # Create demand
    resp = client.post("/api/demands", json={
        "description": "Need observation",
        "bounty_amount": 50.0,
    }, headers=ha)
    demand_id = resp.json()["id"]

    # Accept
    resp = client.post(f"/api/demands/{demand_id}/accept", json={
        "agent_id": b["id"],
    }, headers=ha)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    # Complete → enters verifying (not completed)
    resp = client.post(f"/api/demands/{demand_id}/complete", headers=ha)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verifying"
    assert data["verification_id"] is not None
    assert data["verification_votes"] == 0
    assert data["verification_required"] == 5

    # Bounty still frozen, not settled yet
    wallet_a = client.get("/api/wallet", headers=ha).json()
    assert wallet_a["frozen_balance"] == 50.0
    assert wallet_a["balance"] == 50.0


def test_demand_zero_bounty_skips_verification(client):
    """Test: complete with zero bounty goes straight to completed."""
    a, b = _register_two_agents(client)
    ha = {"X-API-Key": a["api_key"]}

    resp = client.post("/api/demands", json={
        "description": "Free task",
        "bounty_amount": 0.0,
    }, headers=ha)
    demand_id = resp.json()["id"]

    client.post(f"/api/demands/{demand_id}/accept", json={
        "agent_id": b["id"],
    }, headers=ha)

    resp = client.post(f"/api/demands/{demand_id}/complete", headers=ha)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_close_demand_refunds_bounty(client):
    a, _ = _register_two_agents(client)
    ha = {"X-API-Key": a["api_key"]}

    resp = client.post("/api/demands", json={
        "description": "Will cancel",
        "bounty_amount": 20.0,
    }, headers=ha)
    demand_id = resp.json()["id"]

    resp = client.post(f"/api/demands/{demand_id}/close", headers=ha)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    wallet = client.get("/api/wallet", headers=ha).json()
    assert wallet["balance"] == 100.0
    assert wallet["frozen_balance"] == 0.0


def test_list_demands(client, auth_headers):
    client.post("/api/demands", json={
        "description": "Demand 1",
    }, headers=auth_headers)
    client.post("/api/demands", json={
        "description": "Demand 2",
    }, headers=auth_headers)

    resp = client.get("/api/demands", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@patch("app.services.matching_service.call_claude_for_matching")
def test_search_with_mock_claude(mock_claude, client):
    a, b = _register_two_agents(client)
    ha = {"X-API-Key": a["api_key"]}

    # Mock Claude response
    mock_claude.return_value = {
        "interpreted_query": {
            "intent": "Find camera capability",
            "required_features": ["camera"],
            "location_context": "Near Tokyo Tower",
        },
        "scored_candidates": [],  # Will be filled dynamically
    }

    resp = client.post("/api/search/capabilities", json={
        "query": "I need eyes near Tokyo Tower",
    }, headers=ha)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matching_method"] in ("claude", "fallback_keyword")
