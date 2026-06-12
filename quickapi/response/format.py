from quickapi.metrics.request_id import new_request_id

ENGINE_NAME = "quickapi"


def make_meta(request_id=None, time_ms: float | None = None, engine: str = ENGINE_NAME, extra=None):
    meta = {
        "request_id": request_id or new_request_id(),
        "time_ms": 0.0 if time_ms is None else time_ms,
        "engine": engine,
    }
    if extra:
        meta.update(extra)
    return meta


def format_success(data=None, status: int = 200, code: str = "OK", message: str = "Success", meta=None):
    return {
        "ok": True,
        "status": status,
        "code": code,
        "message": message,
        "data": data,
        "error": None,
        "meta": meta or make_meta(),
    }


def format_error(
    status: int,
    code: str,
    message: str,
    detail=None,
    error_type: str = "api_error",
    meta=None,
):
    return {
        "ok": False,
        "status": status,
        "code": code,
        "message": message,
        "data": None,
        "error": {
            "type": error_type,
            "detail": detail,
        },
        "meta": meta or make_meta(),
    }
