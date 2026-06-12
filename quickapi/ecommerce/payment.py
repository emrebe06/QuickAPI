from quickapi.ecommerce import errors
from quickapi.response.factory import q


def accepted(payment_id=None):
    return q.accepted({"payment_id": payment_id, "payment": "accepted"})


def failed(provider=None, reason=None):
    return errors.payment_failed(provider, reason)


def timeout(provider=None):
    return errors.provider_timeout(provider)
