from quickapi import QuickAPI, q


def test_ml_engine_scores_attack_payload():
    app = QuickAPI(ml=True)

    @app.post("/payment/checkout", ml_check=True)
    def checkout(ml):
        return q.ok(ml.to_dict())

    response = app.handle(
        "POST",
        "/payment/checkout",
        body={"note": "DROP TABLE users"},
        headers={"Content-Type": "application/json"},
        raw_body=b'{"note":"DROP TABLE users"}',
    )
    data = response.to_dict()["data"]

    assert data["intent"] == "payment_attempt"
    assert data["risk_score"] >= 0.8
    assert data["action"] in {"challenge", "block"}
    assert "sql_injection" in data["reasons"]


def test_ml_engine_allows_normal_read_request():
    app = QuickAPI(ml=True)

    @app.get("/products", ml_check=True)
    def products(ml):
        return q.ok(ml.to_dict())

    response = app.handle("GET", "/products", headers={"User-Agent": "browser", "Accept": "application/json"})
    data = response.to_dict()["data"]

    assert data["risk_score"] < 0.3
    assert data["action"] == "allow"
