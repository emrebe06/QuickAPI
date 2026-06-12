from uuid import uuid4


def new_request_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"
