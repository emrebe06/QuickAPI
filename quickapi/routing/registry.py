from quickapi.routing.route import Route


class RouteRegistry:
    def __init__(self):
        self._routes: list[Route] = []

    def add(self, route: Route) -> Route:
        existing = self.find(route.method, route.path)
        if existing:
            raise ValueError(f"Route already registered: {route.method} {route.path}")
        self._routes.append(route)
        return route

    def find(self, method: str, path: str) -> Route | None:
        method = method.upper()
        for route in self._routes:
            if route.method == method and route.path == path:
                return route
        return None

    def match(self, method: str, path: str):
        method = method.upper()
        method_mismatch = False
        allowed = []
        for route in self._routes:
            path_params = route.match(path)
            if path_params is None:
                continue
            if route.method == method:
                return route, path_params, None
            method_mismatch = True
            allowed.append(route.method)
        if method_mismatch:
            return None, {}, sorted(set(allowed))
        return None, {}, None

    def all(self) -> list[Route]:
        return list(self._routes)

    def describe(self) -> list[dict]:
        return [route.describe() for route in self._routes]
