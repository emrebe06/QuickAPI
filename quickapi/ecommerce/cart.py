from quickapi.ecommerce import errors


def added(product_id, quantity=1):
    from quickapi.response.factory import q

    return q.ok({"product_id": product_id, "quantity": quantity}, "Added to cart")


def out_of_stock(product_id=None):
    return errors.out_of_stock(product_id)
