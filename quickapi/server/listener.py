import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from quickapi.response.factory import q
from quickapi.response.json_response import JSONResponse
from quickapi.server.logging import AccessLogger


class QuickHTTPServer(ThreadingHTTPServer):
    request_queue_size = 2048
    daemon_threads = True
    allow_reuse_address = True


class QuickListener:
    def __init__(self, app, host: str = "127.0.0.1", port: int = 8080, access_log: bool = True):
        self.app = app
        self.host = host
        self.port = port
        self.logger = AccessLogger(access_log)

    def serve(self):
        app = self.app
        logger = self.logger

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                self._quickapi_handle()

            def do_POST(self):
                self._quickapi_handle()

            def do_PUT(self):
                self._quickapi_handle()

            def do_PATCH(self):
                self._quickapi_handle()

            def do_DELETE(self):
                self._quickapi_handle()

            def do_OPTIONS(self):
                self._send(JSONResponse({"ok": True}, status=204, headers=app.cors_headers()))

            def _quickapi_handle(self):
                parsed = urlparse(self.path)
                raw_body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                ip = self._client_ip()
                body = None
                if raw_body:
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                    except json.JSONDecodeError as exc:
                        response_body = q.bad_request(
                            "Invalid JSON body",
                            {
                                "where": "body",
                                "line": exc.lineno,
                                "column": exc.colno,
                                "position": exc.pos,
                                "hint": "Fix the JSON syntax at the reported line and column.",
                            },
                        )
                        response = JSONResponse(response_body, response_body["status"], headers=app.cors_headers())
                        logger.invalid_json(self.command, parsed.path, ip, "Invalid JSON body")
                        self._send(response)
                        return

                query = {key: values[-1] if len(values) == 1 else values for key, values in parse_qs(parsed.query).items()}
                response = app.handle(
                    self.command,
                    parsed.path,
                    body=body,
                    query=query,
                    headers=dict(self.headers),
                    ip=ip,
                    raw_body=raw_body,
                )
                for key, value in app.cors_headers().items():
                    response.headers.setdefault(key, value)
                self._send(response)
                logger.request(self.command, parsed.path, response, ip)

            def _client_ip(self) -> str:
                forwarded = self.headers.get("X-Forwarded-For")
                if forwarded:
                    return forwarded.split(",", 1)[0].strip()
                real_ip = self.headers.get("X-Real-IP")
                if real_ip:
                    return real_ip.strip()
                return self.client_address[0]

            def _send(self, response: JSONResponse):
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                payload = None
                if not hasattr(response, "iter_bytes"):
                    payload = response.to_bytes()
                    self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if response.status != 204:
                    if hasattr(response, "iter_bytes"):
                        for chunk in response.iter_bytes():
                            self.wfile.write(chunk)
                    else:
                        self.wfile.write(payload)

            def log_message(self, *_):
                return

        app.lifecycle.startup()
        server = QuickHTTPServer((self.host, self.port), Handler)
        self.logger.startup(app.config.name, self.host, self.port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.logger.shutdown(app.config.name, "Ctrl+C received, stopping server")
        finally:
            server.server_close()
            app.lifecycle.shutdown()
            self.logger.shutdown(app.config.name, "Server stopped")


def run(app, host: str = "127.0.0.1", port: int = 8080, access_log: bool = True):
    QuickListener(app, host=host, port=port, access_log=access_log).serve()
