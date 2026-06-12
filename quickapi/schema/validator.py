def require_fields(body: dict, fields: list[str]) -> list[str]:
    body = body or {}
    return [field for field in fields if field not in body]
