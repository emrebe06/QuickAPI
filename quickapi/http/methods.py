GET = "GET"
POST = "POST"
PUT = "PUT"
PATCH = "PATCH"
DELETE = "DELETE"
OPTIONS = "OPTIONS"

SUPPORTED_METHODS = {GET, POST, PUT, PATCH, DELETE, OPTIONS}


def normalize_method(method: str) -> str:
    return method.strip().upper()
