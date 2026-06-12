from quickapi.ecommerce import cart, ecommerce_error


def test_cart_added_response():
    response = cart.added(product_id=7, quantity=2)

    assert response["status"] == 200
    assert response["data"] == {"product_id": 7, "quantity": 2}


def test_out_of_stock_response():
    response = ecommerce_error.out_of_stock(product_id=42)

    assert response["status"] == 409
    assert response["code"] == "CONFLICT"
    assert response["error"]["detail"]["product_id"] == 42
