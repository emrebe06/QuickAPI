from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class DependencyContext:
    app: Any
    request: Any
    route: Any = None
    path_params: dict[str, str] | None = None
    ml: Any = None


@dataclass
class DependencyProvider:
    name: str
    factory: Callable[..., Any]
    cache: bool = True


class DependencyContainer:
    def __init__(self, app=None):
        self.app = app
        self._providers: dict[str, DependencyProvider] = {}

    def register(self, name: str, factory: Callable[..., Any], *, cache: bool = True):
        self._providers[name] = DependencyProvider(name=name, factory=factory, cache=cache)
        return factory

    def decorator(self, name: str | None = None, *, cache: bool = True):
        def wrapper(factory: Callable[..., Any]):
            self.register(name or factory.__name__, factory, cache=cache)
            return factory

        return wrapper

    def has(self, name: str) -> bool:
        return name in self._providers

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": provider.name, "cache": provider.cache, "factory": getattr(provider.factory, "__name__", repr(provider.factory))}
            for provider in sorted(self._providers.values(), key=lambda item: item.name)
        ]

    def resolve_many(self, names: list[str], context: DependencyContext) -> dict[str, Any]:
        cache: dict[str, Any] = {}
        resolved = {}
        for name in dict.fromkeys(names):
            resolved[name] = self.resolve(name, context, cache)
        return resolved

    async def resolve_many_async(self, names: list[str], context: DependencyContext) -> dict[str, Any]:
        cache: dict[str, Any] = {}
        resolved = {}
        for name in dict.fromkeys(names):
            resolved[name] = await self.resolve_async(name, context, cache)
        return resolved

    def resolve(self, name: str, context: DependencyContext, cache: dict[str, Any] | None = None) -> Any:
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Dependency '{name}' is not registered")
        cache = cache if cache is not None else {}
        if provider.cache and name in cache:
            return cache[name]
        value = self._invoke(provider.factory, context)
        if inspect.isawaitable(value):
            raise RuntimeError(f"Dependency '{name}' is async; use ASGI/handle_async for this route")
        if provider.cache:
            cache[name] = value
        return value

    async def resolve_async(self, name: str, context: DependencyContext, cache: dict[str, Any] | None = None) -> Any:
        provider = self._providers.get(name)
        if provider is None:
            raise KeyError(f"Dependency '{name}' is not registered")
        cache = cache if cache is not None else {}
        if provider.cache and name in cache:
            return cache[name]
        value = self._invoke(provider.factory, context)
        if inspect.isawaitable(value):
            value = await value
        if provider.cache:
            cache[name] = value
        return value

    def _invoke(self, factory: Callable[..., Any], context: DependencyContext) -> Any:
        signature = inspect.signature(factory)
        kwargs = {}
        for name in signature.parameters:
            if name == "context":
                kwargs[name] = context
            elif name == "request":
                kwargs[name] = context.request
            elif name == "app":
                kwargs[name] = context.app
            elif name == "route":
                kwargs[name] = context.route
            elif name == "path_params":
                kwargs[name] = context.path_params or {}
            elif name == "ml":
                kwargs[name] = context.ml
        return factory(**kwargs)
