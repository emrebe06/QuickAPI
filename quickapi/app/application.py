import os
import inspect
from time import perf_counter

from quickapi.app.config import QuickAPIConfig
from quickapi.agents.backend import AgentBackend
from quickapi.app.lifecycle import Lifecycle
from quickapi.bridge.native_bridge import NativeBridge
from quickapi.bridge.native_runtime import NativeRuntime
from quickapi.dependencies import DependencyContainer, DependencyContext
from quickapi.db.adapters import DatabaseRegistry
from quickapi.docs.html import render_docs_html
from quickapi.docs.openapi import build_openapi
from quickapi.http.request import Request
from quickapi.jobs.queue import JobQueue
from quickapi.llm.gateway import LLMGateway
from quickapi.metrics.request_id import new_request_id
from quickapi.metrics.timing import elapsed_ms
from quickapi.middleware import MiddlewareChain, MiddlewareContext
from quickapi.ml.engine import MLEngine
from quickapi.ml.guard import GuardConfig, MLGuard
from quickapi.ml.synaptic import SynapticLayer
from quickapi.plugins.manager import PluginManager
from quickapi.response.factory import q
from quickapi.response.file_response import FileResponse, safe_file_response
from quickapi.response.json_response import JSONResponse
from quickapi.routing.router import Router
from quickapi.security.guard import SecurityGuard
from quickapi.security.cors import DEFAULT_CORS_HEADERS
from quickapi.security.tokens import token_from_header
from quickapi.server.listener import QuickListener
from quickapi.schema.validator import validate_payload, validate_runtime_shape
from quickapi.schema.standards import create_default_schema_registry
from quickapi.tools.runner import ToolRunner
from quickapi.webhooks.processor import WebhookProcessor


class QuickAPI:
    def __init__(self, name: str = "QuickAPI", secure: bool = False, ml: bool = False, docs: bool = True, **kwargs):
        self.config = QuickAPIConfig(name=name, secure=secure, ml=ml, docs=docs, **kwargs)
        self.router = Router()
        self.dependencies = DependencyContainer(self)
        self.middleware = MiddlewareChain(self)
        self.lifecycle = Lifecycle()
        self.security = SecurityGuard(enabled=secure, max_body_size=self.config.max_body_size)
        self.ml_engine = MLEngine(enabled=ml, model_path=self.config.ml_model_path)
        self.native_bridge = NativeBridge()
        self.native_runtime = NativeRuntime(self.config.native_library) if self.config.native_library else NativeRuntime()
        self.synaptic = SynapticLayer(
            enabled=self.config.synaptic,
            ml_engine=self.ml_engine,
            native_runtime=self.native_runtime,
            max_body_size=self.config.max_body_size,
        )
        self.ml_guard = MLGuard(
            config=GuardConfig(
                enabled=bool(self.config.ml_guard or self.config.synaptic or self.config.ml),
                block_enabled=self.config.ml_guard_block,
                strict_validation=self.config.ml_guard_strict_validation,
                max_body_size=self.config.max_body_size,
                max_string_length=self.config.ml_guard_max_string_length,
                max_array_length=self.config.ml_guard_max_array_length,
                max_object_keys=self.config.ml_guard_max_object_keys,
            ),
            ml_engine=self.ml_engine,
            synaptic_layer=self.synaptic,
            native_runtime=self.native_runtime,
        )
        self.jobs = JobQueue(max_workers=self.config.job_workers, max_pending=self.config.job_max_pending)
        self.plugins = PluginManager(granted_permissions=self.config.plugin_permissions)
        self.tools = ToolRunner(
            allowed_bins=self.config.local_tools_allowed_bins,
            default_timeout=self.config.local_tools_timeout,
            workspace_root=self.config.local_tools_root,
        )
        self.llm = LLMGateway()
        self.databases = DatabaseRegistry()
        self.schemas = create_default_schema_registry()
        self.webhooks = WebhookProcessor()
        self.agents = AgentBackend(self)
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

    def dependency(self, name: str | None = None, factory=None, *, cache: bool = True):
        if factory is not None:
            return self.dependencies.register(name or factory.__name__, factory, cache=cache)
        return self.dependencies.decorator(name, cache=cache)

    def use(self, middleware=None):
        return self.middleware.add(middleware)

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
            context = MiddlewareContext(app=self, request=request)
            return self.middleware.run(context, lambda next_request: self._handle_request_sync(next_request, start, request_id))
        except Exception as exc:
            return self._finalize(q.server_error(detail=str(exc)), request_id, elapsed_ms(start))

    async def handle_async(self, method: str, path: str, body=None, query=None, headers=None, ip: str = "127.0.0.1", raw_body=b""):
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
            context = MiddlewareContext(app=self, request=request)
            return await self.middleware.run_async(context, lambda next_request: self._handle_request_async(next_request, start, request_id))
        except Exception as exc:
            return self._finalize(q.server_error(detail=str(exc)), request_id, elapsed_ms(start))

    def _handle_request_sync(self, request: Request, start: float, request_id: str):
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

            validation_issues = self._collect_validation_issues(route, request, path_params)
            guard_report = self.ml_guard.inspect(
                request,
                route=route,
                path_params=path_params,
                validation_issues=validation_issues,
            )
            request.synaptic = guard_report.to_dict()
            if guard_report.blocked and not validation_issues:
                return self._finalize(
                    q.forbidden(
                        "Request blocked by QuickAPI ML Guard",
                        {
                            "guard": guard_report.to_dict(),
                            "hint": "Fix the reported signal or disable/tune ml_guard for this trusted route.",
                        },
                    ),
                    request_id,
                    elapsed_ms(start),
                )

            validation_response = self._validation_response(validation_issues, guard_report)
            if validation_response is not None:
                return self._finalize(validation_response, request_id, elapsed_ms(start))

            ml_result = self.ml_engine.analyze(request) if route.ml_check else None
            request.dependencies = self._resolve_dependencies(route, request, path_params, ml_result)
            result = self.router.dispatch_route(route, request, path_params, ml_result)
            return self._finalize(result, request_id, elapsed_ms(start))
        except Exception as exc:
            return self._finalize(q.server_error(detail=str(exc)), request_id, elapsed_ms(start))

    async def _handle_request_async(self, request: Request, start: float, request_id: str):
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

            validation_issues = self._collect_validation_issues(route, request, path_params)
            guard_report = self.ml_guard.inspect(
                request,
                route=route,
                path_params=path_params,
                validation_issues=validation_issues,
            )
            request.synaptic = guard_report.to_dict()
            if guard_report.blocked and not validation_issues:
                return self._finalize(
                    q.forbidden(
                        "Request blocked by QuickAPI ML Guard",
                        {
                            "guard": guard_report.to_dict(),
                            "hint": "Fix the reported signal or disable/tune ml_guard for this trusted route.",
                        },
                    ),
                    request_id,
                    elapsed_ms(start),
                )

            validation_response = self._validation_response(validation_issues, guard_report)
            if validation_response is not None:
                return self._finalize(validation_response, request_id, elapsed_ms(start))

            ml_result = self.ml_engine.analyze(request) if route.ml_check else None
            request.dependencies = await self._resolve_dependencies_async(route, request, path_params, ml_result)
            result = await self.router.dispatch_route_async(route, request, path_params, ml_result)
            return self._finalize(result, request_id, elapsed_ms(start))
        except Exception as exc:
            return self._finalize(q.server_error(detail=str(exc)), request_id, elapsed_ms(start))

    def run(self, host: str | None = None, port: int | None = None, access_log: bool = True):
        host = host or self.config.host
        port = port or self.config.port
        QuickListener(self, host=host, port=port, access_log=access_log).serve()

    def asgi(self):
        from quickapi.asgi import QuickASGIApp

        return QuickASGIApp(self)

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

    def plugin(self, name: str, **options):
        return self.plugins.decorator(name, **options)

    def webhook(self, event: str, **options):
        return self.webhooks.decorator(event, **options)

    def register_schema(self, name: str, schema: dict, *, version: str = "1.0.0", description: str = "", tags: list[str] | None = None):
        self.schemas.register(name, schema, version=version, description=description, tags=tags)
        return self

    def runtime_status(self):
        native = self.native_runtime.runtime_summary()
        return {
            "name": self.config.name,
            "python": {
                "docs": self.config.docs,
                "secure": self.config.secure,
                "ml": self.config.ml,
                "ml_model": self.ml_engine.model_info(),
                "ml_guard": self.ml_guard.config.enabled,
                "job_workers": self.config.job_workers,
                "job_queue": self.jobs.stats(),
                "routes": len(self.routes),
                "dependencies": len(self.dependencies.list()),
                "middleware": len(self.middleware.list()),
            },
            "native": native,
            "features": {
                "streaming_files": True,
                "job_queue": True,
                "ml_engine": True,
                "ml_guard": True,
                "security_guard": True,
                "plugins": True,
                "llm_gateway": True,
                "database_registry": True,
                "schema_registry": True,
                "dependency_injection": True,
                "middleware": True,
                "asgi_adapter": True,
                "webhooks": True,
                "agent_backend": True,
                "local_tools_enabled": self.config.local_tools_enabled,
                "agent_backend_enabled": self.config.agent_backend_enabled,
                "plugin_permissions": sorted(set(self.config.plugin_permissions or [])),
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
        if request.method == "GET" and request.path == "/quick/plugins":
            if not self.config.plugins_enabled:
                return q.forbidden("Plugin runtime is disabled")
            return q.ok({"plugins": self.plugins.list()})
        if request.method == "GET" and request.path.startswith("/quick/plugins/"):
            if not self.config.plugins_enabled:
                return q.forbidden("Plugin runtime is disabled")
            name = request.path.rsplit("/", 1)[-1]
            plugin = self.plugins.describe(name)
            return q.ok(plugin) if plugin else q.not_found("Plugin not found", {"plugin": name})
        if request.method == "POST" and request.path == "/quick/plugins/call":
            if not self.config.plugins_enabled:
                return q.forbidden("Plugin runtime is disabled")
            body = request.body or {}
            result = self.plugins.call(body.get("plugin", ""), body.get("action", "run"), **(body.get("args") or {}))
            return q.ok(result.to_dict()) if result.ok else q.error(400, "PLUGIN_CALL_FAILED", "Plugin call failed", result.to_dict())
        if request.method == "GET" and request.path == "/quick/llm/providers":
            if not self.config.llm_gateway_enabled:
                return q.forbidden("LLM gateway is disabled")
            return q.ok({"providers": self.llm.list()})
        if request.method == "POST" and request.path == "/quick/llm/complete":
            if not self.config.llm_gateway_enabled:
                return q.forbidden("LLM gateway is disabled")
            body = request.body or {}
            result = self.llm.complete(
                body.get("messages") or [{"role": "user", "content": body.get("prompt", "")}],
                provider=body.get("provider", "echo"),
                model=body.get("model", "echo-local"),
                **(body.get("options") or {}),
            )
            return q.ok(result.to_dict()) if result.ok else q.error(502, "LLM_GATEWAY_FAILED", "LLM provider failed", result.to_dict())
        if request.method == "GET" and request.path == "/quick/databases":
            return q.ok({"databases": self.databases.list(), "health": self.databases.health()})
        if request.method == "GET" and request.path == "/quick/schemas":
            return q.ok({"schemas": self.schemas.list()})
        if request.method == "GET" and request.path == "/quick/dependencies":
            return q.ok({"dependencies": self.dependencies.list(), "middleware": self.middleware.list()})
        if request.method == "POST" and request.path == "/quick/tools/run":
            if not self.config.local_tools_enabled:
                return q.forbidden(
                    "Local tool runner is disabled",
                    {"hint": "Enable QuickAPI(..., local_tools_enabled=True) only for trusted local/internal services."},
                )
            body = request.body or {}
            result = self.tools.run(body.get("command") or [], cwd=body.get("cwd"), timeout=body.get("timeout"))
            return q.ok(result.to_dict()) if result.ok else q.error(400, "TOOL_RUN_FAILED", "Tool execution failed", result.to_dict())
        if request.method == "POST" and request.path == "/quick/tools/ffmpeg":
            if not self.config.local_tools_enabled:
                return q.forbidden(
                    "Local tool runner is disabled",
                    {"hint": "Enable QuickAPI(..., local_tools_enabled=True) only for trusted local/internal services."},
                )
            body = request.body or {}
            result = self.tools.ffmpeg_convert(body.get("source", ""), body.get("target", ""), extra=body.get("extra") or [], timeout=body.get("timeout", 300.0))
            return q.ok(result.to_dict()) if result.ok else q.error(400, "FFMPEG_FAILED", "FFmpeg conversion failed", result.to_dict())
        if request.method == "POST" and request.path == "/quick/webhooks/dispatch":
            if not self.config.webhooks_enabled:
                return q.forbidden("Webhook runtime is disabled")
            body = request.body or {}
            result = self.webhooks.dispatch(
                body.get("event", ""),
                body.get("payload") or {},
                raw_body=request.raw_body,
                signature=request.headers.get("X-QuickAPI-Signature"),
            )
            return q.ok(result.to_dict()) if result.ok else q.error(400, "WEBHOOK_FAILED", "Webhook dispatch failed", result.to_dict())
        if request.method == "POST" and request.path == "/quick/agents/run":
            if not self.config.agent_backend_enabled:
                return q.forbidden(
                    "Agent backend is disabled",
                    {"hint": "Enable QuickAPI(..., agent_backend_enabled=True) only after configuring plugin/tool permissions."},
                )
            body = request.body or {}
            return q.ok(
                self.agents.run(
                    body.get("goal", ""),
                    tools=body.get("tools") or [],
                    llm_provider=body.get("llm_provider", "echo"),
                    model=body.get("model", "echo-local"),
                )
            )
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
        issues = self._collect_validation_issues(route, request, path_params)
        return self._validation_response(issues, None)

    def _dependency_names_for_route(self, route) -> list[str]:
        names = list(route.dependencies or [])
        try:
            signature = inspect.signature(route.handler)
        except (TypeError, ValueError):
            return names
        for name in signature.parameters:
            if self.dependencies.has(name):
                names.append(name)
        return list(dict.fromkeys(names))

    def _resolve_dependencies(self, route, request: Request, path_params: dict[str, str], ml_result):
        names = self._dependency_names_for_route(route)
        if not names:
            return {}
        context = DependencyContext(app=self, request=request, route=route, path_params=path_params, ml=ml_result)
        return self.dependencies.resolve_many(names, context)

    async def _resolve_dependencies_async(self, route, request: Request, path_params: dict[str, str], ml_result):
        names = self._dependency_names_for_route(route)
        if not names:
            return {}
        context = DependencyContext(app=self, request=request, route=route, path_params=path_params, ml=ml_result)
        return await self.dependencies.resolve_many_async(names, context)

    def _collect_validation_issues(self, route, request: Request, path_params: dict[str, str]):
        issues = []
        issues.extend(
            validate_runtime_shape(
                request.body,
                location="body",
                max_string_length=self.config.ml_guard_max_string_length,
                max_array_length=self.config.ml_guard_max_array_length,
                max_object_keys=self.config.ml_guard_max_object_keys,
            )
            if request.body is not None and (self.config.ml_guard or self.config.ml or self.config.synaptic)
            else []
        )
        issues.extend(validate_payload(path_params, self.schemas.resolve(route.path_schema), location="path"))
        issues.extend(validate_payload(request.query, self.schemas.resolve(route.query_schema), location="query"))
        issues.extend(validate_payload(request.body, self.schemas.resolve(route.body_schema), location="body"))
        return issues

    def _validation_response(self, issues: list[dict], guard_report):
        if not issues:
            return None
        detail = {
            "issues": issues,
            "hint": "Fix the fields listed in detail. The 'where' key points to the exact request location.",
        }
        if guard_report is not None:
            detail["guard"] = guard_report.to_dict()
        return q.validation(
            "Request validation failed",
            detail,
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
