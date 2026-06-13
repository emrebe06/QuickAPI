from time import perf_counter

from quickapi.app.config import QuickAPIConfig
from quickapi.app.lifecycle import Lifecycle
from quickapi.bridge.native_bridge import NativeBridge
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
from quickapi.server.listener import QuickListener


class QuickAPI:
    def __init__(self, name: str = "QuickAPI", secure: bool = False, ml: bool = False, docs: bool = True, **kwargs):
        self.config = QuickAPIConfig(name=name, secure=secure, ml=ml, docs=docs, **kwargs)
        self.router = Router()
        self.lifecycle = Lifecycle()
        self.security = SecurityGuard(enabled=secure, max_body_size=self.config.max_body_size)
        self.ml_engine = MLEngine(enabled=ml)
        self.native_bridge = NativeBridge()
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

            route, _, _ = self.router.registry.match(request.method, request.path)
            ml_result = self.ml_engine.analyze(request) if route and route.ml_check else None
            result = self.router.dispatch(request, ml_result)
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

    def _handle_builtin(self, request: Request):
        if request.method == "GET" and request.path in {"/docs", "/quick"}:
            if not self.config.docs:
                return q.not_found()
            return JSONResponse(render_docs_html(self), status=200, headers={"Content-Type": "text/html; charset=utf-8"})
        if request.method == "GET" and request.path == "/openapi.json":
            if not self.config.docs:
                return q.not_found()
            return q.ok(build_openapi(self))
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
