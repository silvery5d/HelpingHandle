def _register_agents(client, count):
    """Register multiple agents, return list of (id, api_key) tuples."""
    agents = []
    for i in range(count):
        resp = client.post("/api/agents/register", json={
            "name": f"Agent-{i}",
            "location": {"latitude": 35.6586 + i * 0.001, "longitude": 139.7454},
        })
        data = resp.json()
        agents.append({"id": data["id"], "api_key": data["api_key"]})
    return agents


def _setup_verifying_demand(client, requester, executor, bounty=50.0):
    """Create a demand, accept it, and call complete to enter verifying state. Returns demand_id."""
    ha = {"X-API-Key": requester["api_key"]}

    resp = client.post("/api/demands", json={
        "description": "Task requiring verification",
        "bounty_amount": bounty,
    }, headers=ha)
    demand_id = resp.json()["id"]

    client.post(f"/api/demands/{demand_id}/accept", json={
        "agent_id": executor["id"],
    }, headers=ha)

    client.post(f"/api/demands/{demand_id}/complete", headers=ha)
    return demand_id


def test_full_verification_lifecycle(client):
    """Test: create → accept → complete → 5 votes → auto-settle."""
    agents = _register_agents(client, 7)  # requester + executor + 5 verifiers
    requester, executor = agents[0], agents[1]
    verifiers = agents[2:]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor, bounty=50.0)

    # Get verification
    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    assert resp.status_code == 200
    verification = resp.json()
    assert verification["status"] == "pending"
    assert verification["current_votes"] == 0
    assert verification["required_votes"] == 5
    verification_id = verification["id"]

    # Cast 4 votes — not enough yet
    for i in range(4):
        resp = client.post(
            f"/api/verifications/{verification_id}/vote",
            headers={"X-API-Key": verifiers[i]["api_key"]},
        )
        assert resp.status_code == 201

    # Demand still in verifying state
    resp = client.get(f"/api/demands/{demand_id}", headers=ha)
    assert resp.json()["status"] == "verifying"

    # Bounty still frozen
    wallet_a = client.get("/api/wallet", headers=ha).json()
    assert wallet_a["frozen_balance"] == 50.0

    # 5th vote — triggers auto-settlement
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": verifiers[4]["api_key"]},
    )
    assert resp.status_code == 201

    # Demand now completed
    resp = client.get(f"/api/demands/{demand_id}", headers=ha)
    assert resp.json()["status"] == "completed"

    # Verification approved
    resp = client.get(f"/api/verifications/{verification_id}", headers=ha)
    v_data = resp.json()
    assert v_data["status"] == "approved"
    assert v_data["current_votes"] == 5
    assert v_data["settled_at"] is not None

    # Check wallets — bounty settled
    wallet_a = client.get("/api/wallet", headers=ha).json()
    assert wallet_a["frozen_balance"] == 0.0
    assert wallet_a["balance"] == 50.0  # 100 - 50

    wallet_b = client.get("/api/wallet", headers={"X-API-Key": executor["api_key"]}).json()
    assert wallet_b["balance"] == 149.5  # 100 + 50 * 0.99


def test_requester_cannot_vote(client):
    agents = _register_agents(client, 3)
    requester, executor = agents[0], agents[1]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor)

    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    verification_id = resp.json()["id"]

    # Requester tries to vote
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers=ha,
    )
    assert resp.status_code == 400
    assert "Requester" in resp.json()["detail"]


def test_executor_cannot_vote(client):
    agents = _register_agents(client, 3)
    requester, executor = agents[0], agents[1]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor)

    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    verification_id = resp.json()["id"]

    # Executor tries to vote
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": executor["api_key"]},
    )
    assert resp.status_code == 400
    assert "Executor" in resp.json()["detail"]


def test_duplicate_vote_rejected(client):
    agents = _register_agents(client, 4)
    requester, executor, voter = agents[0], agents[1], agents[2]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor)

    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    verification_id = resp.json()["id"]

    # First vote — ok
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": voter["api_key"]},
    )
    assert resp.status_code == 201

    # Duplicate vote — rejected
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": voter["api_key"]},
    )
    assert resp.status_code == 400
    assert "already voted" in resp.json()["detail"]


def test_list_pending_verifications(client):
    agents = _register_agents(client, 3)
    requester, executor = agents[0], agents[1]
    ha = {"X-API-Key": requester["api_key"]}

    _setup_verifying_demand(client, requester, executor, bounty=10.0)
    _setup_verifying_demand(client, requester, executor, bounty=20.0)

    resp = client.get("/api/verifications", headers=ha)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["verifications"]) == 2


def test_close_demand_during_verifying(client):
    """Closing a demand in VERIFYING state should cancel verification and refund bounty."""
    agents = _register_agents(client, 4)
    requester, executor, voter = agents[0], agents[1], agents[2]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor, bounty=30.0)

    # Cast one vote
    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    verification_id = resp.json()["id"]
    client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": voter["api_key"]},
    )

    # Close the demand
    resp = client.post(f"/api/demands/{demand_id}/close", headers=ha)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    # Verification cancelled
    resp = client.get(f"/api/verifications/{verification_id}", headers=ha)
    assert resp.json()["status"] == "cancelled"

    # Bounty refunded
    wallet = client.get("/api/wallet", headers=ha).json()
    assert wallet["balance"] == 100.0
    assert wallet["frozen_balance"] == 0.0


def test_vote_on_approved_verification_rejected(client):
    """Cannot vote on a verification that has already been settled."""
    agents = _register_agents(client, 8)  # requester + executor + 6 verifiers
    requester, executor = agents[0], agents[1]
    verifiers = agents[2:]
    ha = {"X-API-Key": requester["api_key"]}

    demand_id = _setup_verifying_demand(client, requester, executor, bounty=10.0)

    resp = client.get(f"/api/verifications/demand/{demand_id}", headers=ha)
    verification_id = resp.json()["id"]

    # Cast 5 votes to settle
    for i in range(5):
        client.post(
            f"/api/verifications/{verification_id}/vote",
            headers={"X-API-Key": verifiers[i]["api_key"]},
        )

    # 6th vote on now-approved verification
    resp = client.post(
        f"/api/verifications/{verification_id}/vote",
        headers={"X-API-Key": verifiers[5]["api_key"]},
    )
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"]
