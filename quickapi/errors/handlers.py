from quickapi.errors.exceptions import QuickAPIError
from quickapi.response.factory import q


def handle_exception(exc: Exception):
    if isinstance(exc, QuickAPIError):
        return q.error(exc.status, exc.code, exc.message, exc.detail)
    return q.server_error(detail=str(exc))
