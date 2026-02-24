def test_get_wallet(client, auth_headers):
    resp = client.get("/api/wallet", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 100.0
    assert data["frozen_balance"] == 0.0
    assert data["total"] == 100.0


def test_initial_grant_transaction(client, auth_headers):
    resp = client.get("/api/wallet/transactions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["transactions"][0]["type"] == "initial_grant"
    assert data["transactions"][0]["amount"] == 100.0
