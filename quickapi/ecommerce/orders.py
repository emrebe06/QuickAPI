from quickapi.response.factory import q


def created(order_id=None):
    return q.created({"order_id": order_id}, "Order created")


def status(order_id=None, state="pending"):
    return q.ok({"order_id": order_id, "status": state})
