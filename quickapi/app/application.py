import os
from time import perf_counter

from quickapi.app.config import QuickAPIConfig
from quickapi.app.lifecycle import Lifecycle
from quickapi.bridge.native_bridge import NativeBridge
from quickapi.bridge.native_runtime import NativeRuntime
from quickapi.docs.html import render_docs_html
from quickapi.docs.openapi import build_openapi
from quickapi.http.request import Request
from quickapi.jobs.queue import JobQueue
from quickapi.metrics.request_id import new_request_id
from quickapi.metrics.timing import elapsed_ms
from quickapi.ml.engine import MLEngine
from quickapi.response.factory import q
from quickapi.response.file_response import FileResponse, safe_file_response
from quickapi.response.json_response import JSONResponse
from quickapi.routing.router import Router
from quickapi.security.guard import SecurityGuard
from quickapi.security.cors import DEFAULT_CORS_HEADERS
from quickapi.security.tokens import token_from_header
from quickapi.server.listener import QuickListener
from quickapi.schema.validator import validate_payload


class QuickAPI:
    def __init__(self, name: str = "QuickAPI", secure: bool = False, ml: bool = False, docs: bool = True, **kwargs):
        self.config = QuickAPIConfig(name=name, secure=secure, ml=ml, docs=docs, **kwargs)
        self.router = Router()
        self.lifecycle = Lifecycle()
        self.security = SecurityGuard(enabled=secure, max_body_size=self.config.max_body_size)
        self.ml_engine = MLEngine(enabled=ml)
        self.native_bridge = NativeBridge()
        self.native_runtime = NativeRuntime(self.config.native_library) if self.config.native_library else NativeRuntime()
        self.jobs = JobQueue(max_workers=self.config.job_workers)
        self.lifecycle.on_shutdown(self.jobs.shutdown)

    @property
    def routes(self):
        return self.router.registry.all()

    def route(self, method: str, path: str, **metadata):
        return self.router.route(method, path, **metadata)

    def get(self, path: str, **metadata):
        return self.route("GET", path, **metadata)

    def post(self, path: str, **metadata):
        return self.route("POST", path, **metadata)

    def put(self, path: str, **metadata):
        return self.route("PUT", path, **metadata)

    def patch(self, path: str, **metadata):
        return self.route("PATCH", path, **metadata)

    def delete(self, path: str, **metadata):
        return self.route("DELETE", path, **metadata)

    def native_post(self, path: str, library: str, symbol: str, **metadata):
        native_handler = self.native_bridge.make_handler(library, symbol)
        metadata["native"] = {"library": library, "symbol": symbol}
        return self.router.add_route("POST", path, native_handler, **metadata)

    def handle(self, method: str, path: str, body=None, query=None, headers=None, ip: str = "127.0.0.1", raw_body=b""):
        start = perf_counter()
        request_id = new_request_id()
        request = Request.build(
            method=method,
            path=path,
            body=body,
            query=query,
            headers=headers,
            ip=ip,
            request_id=request_id,
            raw_body=raw_body,
        )

        try:
            built_in = self._handle_builtin(request)
            if built_in is not None:
                return self._finalize(built_in, request_id, elapsed_ms(start))

            guard_response = self.security.check(request)
            if guard_response is not None:
                return self._finalize(guard_response, request_id, elapsed_ms(start))

            route, path_params, allowed = self.router.registry.match(request.method, request.path)
            if allowed:
                return self._finalize(q.method_not_allowed(detail={"allowed": allowed}), request_id, elapsed_ms(start))
            if route is None:
                return self._finalize(
                    q.not_found(detail=f"No route found for {request.method} {request.path}"),
                    request_id,
                    elapsed_ms(start),
                )

            auth_response = self._authorize(route, request)
            if auth_response is not None:
                return self._finalize(auth_response, request_id, elapsed_ms(start))

            validation_response = self._validate_route_input(route, request, path_params)
            if validation_response is not None:
                return self._finalize(validation_response, request_id, elapsed_ms(start))

            ml_result = self.ml_engine.analyze(request) if route.ml_check else None
            result = self.router.dispatch_route(route, request, path_params, ml_result)
            return self._finalize(result, request_id, elapsed_ms(start))
        except Exception as exc:
            return self._finalize(q.server_error(detail=str(exc)), request_id, elapsed_ms(start))

    def run(self, host: str | None = None, port: int | None = None, access_log: bool = True):
        host = host or self.config.host
        port = port or self.config.port
        QuickListener(self, host=host, port=port, access_log=access_log).serve()

    def cors_headers(self) -> dict[str, str]:
        return dict(DEFAULT_CORS_HEADERS)

    def file(self, path, *, download_name: str | None = None, headers: dict[str, str] | None = None):
        response = FileResponse(path, download_name=download_name)
        if headers:
            response.headers.update(headers)
        return response

    def static_file(self, root, path: str, *, download: bool = False):
        response = safe_file_response(root, path, download=download)
        if response is None:
            return q.not_found("Static file was not found")
        return response

    def submit_job(self, func, *args, name: str | None = None, **kwargs):
        record = self.jobs.submit(func, *args, name=name, **kwargs)
        return q.accepted(
            {
                "job_id": record.id,
                "status": record.status,
                "status_url": f"/quick/jobs/{record.id}",
            },
            message="Job accepted",
        )

    def runtime_status(self):
        native = self.native_runtime.runtime_summary()
        return {
            "name": self.config.name,
            "python": {
                "docs": self.config.docs,
                "secure": self.config.secure,
                "ml": self.config.ml,
                "job_workers": self.config.job_workers,
                "routes": len(self.routes),
            },
            "native": native,
            "features": {
                "streaming_files": True,
                "job_queue": True,
                "ml_engine": True,
                "security_guard": True,
            },
        }

    def _handle_builtin(self, request: Request):
        if request.method == "GET" and request.path in {"/docs", "/quick"}:
            if not self.config.docs:
                return q.not_found()
            return JSONResponse(render_docs_html(self), status=200, headers={"Content-Type": "text/html; charset=utf-8"})
        if request.method == "GET" and request.path == "/openapi.json":
            if not self.config.docs:
                return q.not_found()
            return q.ok(build_openapi(self))
        if request.method == "GET" and request.path == "/quick/runtime":
            return q.ok(self.runtime_status(), message="Runtime status")
        if request.method == "GET" and request.path == "/quick/jobs":
            return q.ok({"jobs": self.jobs.list()})
        if request.path.startswith("/quick/jobs/"):
            job_id = request.path.rsplit("/", 1)[-1]
            record = self.jobs.get(job_id)
            if record is None:
                return q.not_found("Job not found", {"job_id": job_id})
            if request.method == "GET":
                return q.ok(record.to_dict(), message="Job status")
            if request.method == "DELETE":
                cancelled = self.jobs.cancel(job_id)
                return q.ok(cancelled.to_dict(), message="Job cancel requested")
        return None

    def _authorize(self, route, request: Request):
        if not route.auth:
            return None

        token = token_from_header(request.headers)
        if not token:
            return q.unauthorized(
                "Authentication required",
                {
                    "where": "headers.Authorization",
                    "expected": "Bearer <token>",
                    "hint": "Send an Authorization header or disable auth for this route.",
                },
            )

        validator = self.config.auth_validator
        if validator is not None:
            result = validator(token, request)
            if result:
                request.auth = result if isinstance(result, dict) else {"token": token, "method": "validator"}
                return None
            return q.forbidden(
                "Token rejected",
                {"where": "headers.Authorization", "hint": "The configured auth validator rejected this token."},
            )

        allowed = set(self.config.auth_tokens or [])
        env_token = os.environ.get("QUICKAPI_AUTH_TOKEN") or os.environ.get("QUICKAPI_TOKEN")
        if env_token:
            allowed.add(env_token)
        if not allowed:
            return q.forbidden(
                "Auth is not configured",
                {
                    "where": "app.config.auth_tokens",
                    "hint": "Pass QuickAPI(..., auth_tokens={'secret'}) or auth_validator=callable.",
                },
            )
        if token not in allowed:
            return q.forbidden(
                "Invalid token",
                {"where": "headers.Authorization", "hint": "Bearer token did not match configured auth tokens."},
            )

        request.auth = {"token": token, "method": "bearer"}
        return None

    def _validate_route_input(self, route, request: Request, path_params: dict[str, str]):
        issues = []
        issues.extend(validate_payload(path_params, route.path_schema, location="path"))
        issues.extend(validate_payload(request.query, route.query_schema, location="query"))
        issues.extend(validate_payload(request.body, route.body_schema, location="body"))
        if not issues:
            return None
        return q.validation(
            "Request validation failed",
            {
                "issues": issues,
                "hint": "Fix the fields listed in detail. The 'where' key points to the exact request location.",
            },
        )

    def _finalize(self, result, request_id: str, time_ms: float):
        headers = None
        if isinstance(result, FileResponse):
            result.headers.setdefault("X-Request-ID", request_id)
            result.headers.setdefault("X-Response-Time-MS", str(time_ms))
            return result
        if isinstance(result, JSONResponse):
            body = result.to_dict()
            status = result.status
            headers = result.headers
        elif isinstance(result, dict) and {"ok", "status", "code", "message", "data", "error", "meta"}.issubset(result):
            body = result
            status = int(body.get("status", 200))
        else:
            body = q.ok(result)
            status = body["status"]

        if not isinstance(body, dict):
            return JSONResponse(body=body, status=status, headers=headers or {})
        body.setdefault("meta", {})
        body["meta"].update({"request_id": request_id, "time_ms": time_ms, "engine": "quickapi"})
        return JSONResponse(body=body, status=status, headers=headers or {})
