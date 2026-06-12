from quickapi.response.factory import q


def out_of_stock(product_id=None):
    return q.conflict("Product is out of stock", {"product_id": product_id})


def price_changed(product_id=None, old_price=None, new_price=None):
    return q.conflict(
        "Product price changed",
        {"product_id": product_id, "old_price": old_price, "new_price": new_price},
    )


def payment_failed(provider=None, reason=None):
    return q.payment_required("Payment failed", {"provider": provider, "reason": reason})


def invalid_coupon(code=None):
    return q.validation("Invalid coupon", {"coupon": code})


def address_invalid(detail=None):
    return q.validation("Invalid address", detail)


def provider_timeout(provider=None):
    return q.timeout("External provider timed out", {"provider": provider})
