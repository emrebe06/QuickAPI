from quickapi import QuickAPI, q

app = QuickAPI("ML Guard API", ml=True)


@app.post("/payment/checkout", errors=[402, 422, 429, 504], ml_check=True, rate_limit="strict")
def checkout(body, ml):
    if ml.risk_score > 0.85:
        return q.too_many_requests("Suspicious request blocked", ml.to_dict())
    return q.ok({"payment": "accepted", "ml": ml.to_dict()})


if __name__ == "__main__":
    app.run()
