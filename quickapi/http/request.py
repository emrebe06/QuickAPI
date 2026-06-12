from dataclasses import dataclass, field
from typing import Any

from quickapi.http.headers import Headers, normalize_headers


@dataclass
class Request:
    method: str
    path: str
    body: Any = None
    query: dict[str, Any] = field(default_factory=dict)
    headers: Headers = field(default_factory=Headers)
    ip: str = "127.0.0.1"
    request_id: str | None = None
    raw_body: bytes = b""

    @classmethod
    def build(
        cls,
        method: str,
        path: str,
        body=None,
        query=None,
        headers=None,
        ip: str = "127.0.0.1",
        request_id: str | None = None,
        raw_body: bytes = b"",
    ):
        return cls(
            method=method.upper(),
            path=path,
            body=body,
            query=query or {},
            headers=normalize_headers(headers or {}),
            ip=ip,
            request_id=request_id,
            raw_body=raw_body,
        )
