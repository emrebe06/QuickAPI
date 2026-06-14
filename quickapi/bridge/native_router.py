from __future__ import annotations

import ctypes
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class NativeRouteMatch:
    route: Any
    path_params: dict[str, str]
    allowed: list[str] | None = None
    score: int = -1
    engine: str = "native-router"


class NativeRouteBridge:
    def __init__(self, native_runtime=None):
        self.native_runtime = native_runtime
        self._router = None
        self._token_to_route: dict[str, Any] = {}
        self._enabled = False
        self._configured = False
        self._init_router()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def add(self, route) -> bool:
        if not self._enabled:
            return False
        token = self._token(route)
        ok = self.native_runtime.library.quickapi_router_add(
            self._router,
            route.method.encode("utf-8"),
            route.path.encode("utf-8"),
            token.encode("utf-8"),
        )
        if ok:
            self._token_to_route[token] = route
        return bool(ok)

    def match(self, method: str, path: str) -> NativeRouteMatch | None:
        if not self._enabled:
            return None
        lib = self.native_runtime.library
        method_bytes = method.upper().encode("utf-8")
        path_bytes = path.encode("utf-8")
        raw = lib.quickapi_router_match(self._router, method_bytes, path_bytes)
        if raw:
            token = raw.decode("utf-8")
            route = self._token_to_route.get(token)
            if route is None:
                return None
            params_raw = lib.quickapi_router_params(self._router, method_bytes, path_bytes)
            params = json.loads(params_raw.decode("utf-8")) if params_raw else {}
            score = int(lib.quickapi_router_match_score(self._router, method_bytes, path_bytes))
            return NativeRouteMatch(route=route, path_params=params, score=score)
        allowed_raw = lib.quickapi_router_allowed_methods(self._router, path_bytes)
        if allowed_raw:
            allowed = [item for item in allowed_raw.decode("utf-8").split(",") if item]
            if allowed:
                return NativeRouteMatch(route=None, path_params={}, allowed=sorted(set(allowed)))
        return None

    def close(self):
        if self._router and self.native_runtime and getattr(self.native_runtime, "available", False):
            try:
                self.native_runtime.library.quickapi_router_destroy(self._router)
            except Exception:
                pass
        self._router = None
        self._enabled = False

    def _init_router(self):
        if not self.native_runtime or not getattr(self.native_runtime, "available", False):
            return
        try:
            lib = self.native_runtime.library
            lib.quickapi_router_create.restype = ctypes.c_void_p
            lib.quickapi_router_destroy.argtypes = [ctypes.c_void_p]
            lib.quickapi_router_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            lib.quickapi_router_add.restype = ctypes.c_int
            lib.quickapi_router_match.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            lib.quickapi_router_match.restype = ctypes.c_char_p
            lib.quickapi_router_params.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            lib.quickapi_router_params.restype = ctypes.c_char_p
            lib.quickapi_router_match_score.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            lib.quickapi_router_match_score.restype = ctypes.c_int
            lib.quickapi_router_allowed_methods.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            lib.quickapi_router_allowed_methods.restype = ctypes.c_char_p
            self._router = lib.quickapi_router_create()
            self._enabled = bool(self._router)
            self._configured = True
        except Exception:
            self._router = None
            self._enabled = False

    def _token(self, route) -> str:
        return f"{route.method} {route.path}"
