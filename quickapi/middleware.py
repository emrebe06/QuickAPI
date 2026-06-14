from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MiddlewareContext:
    app: Any
    request: Any
    route: Any = None
    path_params: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


class MiddlewareChain:
    def __init__(self, app=None):
        self.app = app
        self._items: list[Any] = []

    def add(self, middleware=None):
        if middleware is None:
            def wrapper(func):
                self._items.append(func)
                return func
            return wrapper
        self._items.append(middleware)
        return middleware

    def list(self) -> list[dict[str, str]]:
        return [{"name": getattr(item, "__name__", item.__class__.__name__)} for item in self._items]

    def run(self, context: MiddlewareContext, terminal: Callable[[Any], Any]):
        def call_at(index: int, request):
            if index >= len(self._items):
                return terminal(request)
            item = self._items[index]
            next_call = lambda next_request=request: call_at(index + 1, next_request)
            return self._call_sync(item, context, request, next_call)

        return call_at(0, context.request)

    async def run_async(self, context: MiddlewareContext, terminal: Callable[[Any], Any]):
        async def call_at(index: int, request):
            if index >= len(self._items):
                result = terminal(request)
                if inspect.isawaitable(result):
                    result = await result
                return result
            item = self._items[index]

            async def next_call(next_request=request):
                return await call_at(index + 1, next_request)

            return await self._call_async(item, context, request, next_call)

        return await call_at(0, context.request)

    def _call_sync(self, item, context: MiddlewareContext, request, next_call):
        if hasattr(item, "before"):
            maybe_request = item.before(context)
            if maybe_request is not None:
                request = maybe_request
        if callable(item) and not hasattr(item, "before"):
            result = item(request, next_call)
        else:
            result = next_call(request)
        if hasattr(item, "after"):
            after_result = item.after(context, result)
            if after_result is not None:
                result = after_result
        return result

    async def _call_async(self, item, context: MiddlewareContext, request, next_call):
        if hasattr(item, "before"):
            maybe_request = item.before(context)
            if inspect.isawaitable(maybe_request):
                maybe_request = await maybe_request
            if maybe_request is not None:
                request = maybe_request
        if callable(item) and not hasattr(item, "before"):
            result = item(request, next_call)
            if inspect.isawaitable(result):
                result = await result
        else:
            result = await next_call(request)
        if hasattr(item, "after"):
            after_result = item.after(context, result)
            if inspect.isawaitable(after_result):
                after_result = await after_result
            if after_result is not None:
                result = after_result
        return result
