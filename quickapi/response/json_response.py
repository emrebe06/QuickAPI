import json
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class JSONResponse:
    body: Any
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.headers.setdefault("Content-Type", "application/json; charset=utf-8")

    def to_dict(self) -> Any:
        return self.body

    def to_json(self) -> str:
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body, ensure_ascii=False, separators=(",", ":"))

    def to_bytes(self) -> bytes:
        if isinstance(self.body, bytes):
            return self.body
        return self.to_json().encode("utf-8")

    def iter_bytes(self, chunk_size: int = 1024 * 128) -> Iterator[bytes]:
        payload = self.to_bytes()
        for offset in range(0, len(payload), chunk_size):
            yield payload[offset : offset + chunk_size]
