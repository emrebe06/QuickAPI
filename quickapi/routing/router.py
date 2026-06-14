import inspect
from typing import Any

from quickapi.response.factory import q
from quickapi.routing.registry import RouteRegistry
from quickapi.routing.route import Route


class Router:
    def __init__(self, registry: RouteRegistry | None = None):
        self.registry = registry or RouteRegistry()

    def add_route(self, method: str, path: str, handler, **metadata):
        route = Route(path=path, method=method, handler=handler, **metadata)
        return self.registry.add(route)

    def route(self, method: str, path: str, **metadata):
        def decorator(handler):
            self.add_route(method, path, handler, **metadata)
            return handler

        return decorator

    def dispatch(self, request, ml_result=None):
        route, path_params, allowed = self.registry.match(request.method, request.path)
        if allowed:
            return q.method_not_allowed(detail={"allowed": allowed})
        if route is None:
            return q.not_found(detail=f"No route found for {request.method} {request.path}")
        return self.dispatch_route(route, request, path_params, ml_result)

    def dispatch_route(self, route: Route, request, path_params: dict[str, str], ml_result=None):
        return self._call_route(route, request, path_params, ml_result)

    def _call_route(self, route: Route, request, path_params: dict[str, str], ml_result=None):
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
            elif name in path_params:
                kwargs[name] = path_params[name]
        return route.handler(**kwargs)
