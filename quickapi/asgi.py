from __future__ import annotations

import json
from urllib.parse import parse_qs

from quickapi.response.factory import q
from quickapi.response.json_response import JSONResponse


class QuickASGIApp:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope.get("type") != "http":
            await send({"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": b"Unsupported ASGI scope"})
            return

        try:
            raw_body = await self._read_body(receive, int(getattr(self.app.config, "max_body_size", 1024 * 1024)))
        except ValueError as exc:
            response = JSONResponse(
                q.error(
                    413,
                    "PAYLOAD_TOO_LARGE",
                    "Request body is too large",
                    {"where": "body", "hint": str(exc), "max_body_size": getattr(self.app.config, "max_body_size", 1024 * 1024)},
                ),
                413,
                headers=self.app.cors_headers(),
            )
            await self._send_response(send, response)
            return
        headers = self._headers(scope)
        body = None
        if raw_body:
            try:
                body = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                response = JSONResponse(
                    q.bad_request(
                        "Invalid JSON body",
                        {
                            "where": "body",
                            "line": exc.lineno,
                            "column": exc.colno,
                            "position": exc.pos,
                            "hint": "Fix the JSON syntax at the reported line and column.",
                        },
                    ),
                    400,
                    headers=self.app.cors_headers(),
                )
                await self._send_response(send, response)
                return

        query = {
            key: values[-1] if len(values) == 1 else values
            for key, values in parse_qs((scope.get("query_string") or b"").decode("utf-8", errors="ignore")).items()
        }
        client = scope.get("client") or ("127.0.0.1", 0)
        response = await self.app.handle_async(
            scope.get("method", "GET"),
            scope.get("path", "/"),
            body=body,
            query=query,
            headers=headers,
            ip=client[0],
            raw_body=raw_body,
        )
        for key, value in self.app.cors_headers().items():
            response.headers.setdefault(key, value)
        await self._send_response(send, response)

    async def _lifespan(self, receive, send):
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "lifespan.startup":
                try:
                    self.app.lifecycle.startup()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as exc:
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
            elif message_type == "lifespan.shutdown":
                try:
                    self.app.lifecycle.shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception as exc:
                    await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                return

    async def _read_body(self, receive, max_bytes: int) -> bytes:
        chunks: list[bytes] = []
        total = 0
        more = True
        while more:
            message = await receive()
            if message.get("type") == "http.disconnect":
                break
            if message.get("type") != "http.request":
                continue
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("ASGI body exceeded QuickAPI max_body_size.")
            chunks.append(chunk)
            more = bool(message.get("more_body", False))
        return b"".join(chunks)

    def _headers(self, scope) -> dict[str, str]:
        headers = {}
        for key, value in scope.get("headers", []):
            headers[key.decode("latin1")] = value.decode("latin1")
        return headers

    async def _send_response(self, send, response):
        headers = [(str(key).lower().encode("latin1"), str(value).encode("latin1")) for key, value in response.headers.items()]
        await send({"type": "http.response.start", "status": int(response.status), "headers": headers})
        if response.status == 204:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        if hasattr(response, "iter_bytes"):
            iterator = response.iter_bytes()
            first = True
            for chunk in iterator:
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
                first = False
            if first:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            else:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        await send({"type": "http.response.body", "body": response.to_bytes(), "more_body": False})
