HTTP_STATUS = {
    200: ("OK", "OK"),
    201: ("CREATED", "Created"),
    202: ("ACCEPTED", "Accepted"),
    204: ("NO_CONTENT", "No content"),
    400: ("BAD_REQUEST", "Bad request"),
    401: ("UNAUTHORIZED", "Unauthorized"),
    402: ("PAYMENT_REQUIRED", "Payment required"),
    403: ("FORBIDDEN", "Forbidden"),
    404: ("NOT_FOUND", "Not found"),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    409: ("CONFLICT", "Conflict"),
    415: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
    422: ("VALIDATION_ERROR", "Validation error"),
    429: ("TOO_MANY_REQUESTS", "Too many requests"),
    500: ("INTERNAL_SERVER_ERROR", "Internal server error"),
    502: ("BAD_GATEWAY", "Bad gateway"),
    503: ("SERVICE_UNAVAILABLE", "Service unavailable"),
    504: ("GATEWAY_TIMEOUT", "Gateway timeout"),
}


def status_code_name(status: int) -> str:
    return HTTP_STATUS.get(status, ("UNKNOWN", "Unknown"))[0]


def status_message(status: int) -> str:
    return HTTP_STATUS.get(status, ("UNKNOWN", "Unknown"))[1]
