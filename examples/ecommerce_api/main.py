from quickapi import QuickAPI, q
from quickapi.ecommerce import ecommerce_error

app = QuickAPI("Shop API", secure=True, ml=True, docs=True)


@app.get("/health")
def health():
    return q.ok({"status": "running"})


@app.post("/cart/add", errors=[409, 422, 429], ml_check=True, rate_limit="strict")
def add_cart(body, ml):
    product_id = body.get("product_id") if body else None
    quantity = body.get("quantity", 1) if body else 1
    if not product_id:
        return q.validation("product_id is required")
    if quantity <= 0:
        return q.validation("quantity must be greater than zero")
    if product_id == 42:
        return ecommerce_error.out_of_stock(product_id=product_id)
    if ml and ml.risk_score > 0.85:
        return q.too_many_requests("Suspicious request blocked")
    return q.ok({"product_id": product_id, "quantity": quantity})


if __name__ == "__main__":
    app.run()
