import inspect
import asyncio
from typing import Any

from quickapi.response.factory import q
from quickapi.routing.registry import RouteRegistry
from quickapi.routing.route import Route


class Router:
    def __init__(self, registry: RouteRegistry | None = None, native_router=None):
        self.registry = registry or RouteRegistry()
        self.native_router = native_router

    def add_route(self, method: str, path: str, handler, **metadata):
        route = Route(path=path, method=method, handler=handler, **metadata)
        route = self.registry.add(route)
        if self.native_router is not None:
            self.native_router.add(route)
        return route

    def route(self, method: str, path: str, **metadata):
        def decorator(handler):
            self.add_route(method, path, handler, **metadata)
            return handler

        return decorator

    def dispatch(self, request, ml_result=None):
        route, path_params, allowed = self.match(request.method, request.path)
        if allowed:
            return q.method_not_allowed(detail={"allowed": allowed})
        if route is None:
            return q.not_found(detail=f"No route found for {request.method} {request.path}")
        return self.dispatch_route(route, request, path_params, ml_result)

    def match(self, method: str, path: str):
        if self.native_router is not None and self.native_router.enabled:
            native_match = self.native_router.match(method, path)
            if native_match is not None:
                return native_match.route, native_match.path_params, native_match.allowed
        return self.registry.match(method, path)

    def dispatch_route(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        return self._call_route(route, request, path_params, ml_result)

    async def dispatch_route_async(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        return await self._call_route_async(route, request, path_params, ml_result)

    def _call_route(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        kwargs = self._build_kwargs(route, request, path_params, ml_result)
        result = route.handler(**kwargs)
        if inspect.isawaitable(result):
            return asyncio.run(result)
        return result

    async def _call_route_async(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        kwargs = self._build_kwargs(route, request, path_params, ml_result)
        result = route.handler(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def _build_kwargs(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        signature = inspect.signature(route.handler)
        kwargs: dict[str, Any] = {}
        for name in signature.parameters:
            if name == "body":
                kwargs[name] = request.body
            elif name == "query":
                kwargs[name] = request.query
            elif name == "headers":
                kwargs[name] = request.headers
            elif name == "request":
                kwargs[name] = request
            elif name == "auth":
                kwargs[name] = request.auth
            elif name == "ml":
                kwargs[name] = ml_result
            elif name == "state":
                kwargs[name] = request.state
            elif name in request.dependencies:
                kwargs[name] = request.dependencies[name]
            elif name in path_params:
                kwargs[name] = path_params[name]
        return kwargs
