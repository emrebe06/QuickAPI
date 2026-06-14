from __future__ import annotations

import hmac
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable


@dataclass
class WebhookResult:
    ok: bool
    event: str
    data: Any = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "event": self.event, "data": self.data, "error": self.error}


class WebhookProcessor:
    def __init__(self):
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._secrets: dict[str, str] = {}

    def register(self, event: str, handler: Callable[[dict[str, Any]], Any], *, secret: str | None = None):
        self._handlers[event] = handler
        if secret:
            self._secrets[event] = secret
        return handler

    def decorator(self, event: str, *, secret: str | None = None):
        def wrapper(func):
            self.register(event, func, secret=secret)
            return func

        return wrapper

    def verify(self, event: str, raw_body: bytes, signature: str | None) -> bool:
        secret = self._secrets.get(event)
        if not secret:
            return True
        expected = hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
        received = (signature or "").replace("sha256=", "")
        return hmac.compare_digest(expected, received)

    def dispatch(self, event: str, payload: dict[str, Any], *, raw_body: bytes = b"", signature: str | None = None) -> WebhookResult:
        if not self.verify(event, raw_body, signature):
            return WebhookResult(False, event, error={"code": "WEBHOOK_SIGNATURE_INVALID"})
        handler = self._handlers.get(event)
        if handler is None:
            return WebhookResult(False, event, error={"code": "WEBHOOK_HANDLER_NOT_FOUND", "available": sorted(self._handlers)})
        try:
            return WebhookResult(True, event, data=handler(payload))
        except Exception as exc:
            return WebhookResult(False, event, error={"type": exc.__class__.__name__, "message": str(exc)})
