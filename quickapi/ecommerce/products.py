from quickapi.ecommerce import errors
from quickapi.response.factory import q


def found(product):
    return q.ok(product)


def not_found(product_id=None):
    return q.not_found("Product not found", {"product_id": product_id})


def out_of_stock(product_id=None):
    return errors.out_of_stock(product_id)
