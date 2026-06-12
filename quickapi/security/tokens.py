def token_from_header(headers) -> str | None:
    auth = headers.get("Authorization")
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth.strip()


def check_token(headers, expected: str | None = None) -> bool:
    if expected is None:
        return True
    return token_from_header(headers) == expected
