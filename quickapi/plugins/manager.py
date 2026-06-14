from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from enum import StrEnum
from time import perf_counter
from typing import Any, Callable


class PluginPermission(StrEnum):
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    NETWORK = "network"
    SHELL = "shell"
    LLM = "llm"
    DATABASE = "database"
    AUTOMATION = "automation"


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    permissions: set[str] = field(default_factory=set)
    entrypoint: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "permissions": sorted(self.permissions),
            "entrypoint": self.entrypoint,
            "tags": list(self.tags),
        }


@dataclass
class PluginResult:
    ok: bool
    plugin: str
    action: str
    data: Any = None
    error: dict[str, Any] | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plugin": self.plugin,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class PluginManager:
    def __init__(self, *, granted_permissions: set[str] | list[str] | tuple[str, ...] | None = None):
        self._manifests: dict[str, PluginManifest] = {}
        self._handlers: dict[str, dict[str, Callable[..., Any]]] = {}
        self._granted_permissions = set(granted_permissions or [])

    def grant(self, *permissions: str):
        self._granted_permissions.update(str(permission) for permission in permissions)
        return self

    def revoke(self, *permissions: str):
        for permission in permissions:
            self._granted_permissions.discard(str(permission))
        return self

    def register(
        self,
        name: str,
        handler: Callable[..., Any] | None = None,
        *,
        action: str = "run",
        permissions: set[str] | list[str] | tuple[str, ...] | None = None,
        version: str = "0.1.0",
        description: str = "",
        tags: list[str] | None = None,
    ):
        manifest = self._manifests.get(name) or PluginManifest(name=name)
        manifest.version = version
        manifest.description = description or manifest.description
        manifest.permissions = set(manifest.permissions if permissions is None else permissions)
        manifest.tags = tags or manifest.tags
        self._manifests[name] = manifest
        if handler is not None:
            self._handlers.setdefault(name, {})[action] = handler
        return handler

    def decorator(self, name: str, *, action: str = "run", permissions=None, version: str = "0.1.0", description: str = "", tags=None):
        def wrapper(func: Callable[..., Any]):
            self.register(name, func, action=action, permissions=permissions, version=version, description=description, tags=tags)
            return func

        return wrapper

    def load(self, entrypoint: str, *, name: str | None = None) -> PluginManifest:
        module_name, _, attr = entrypoint.partition(":")
        module = importlib.import_module(module_name)
        plugin_obj = getattr(module, attr) if attr else module
        plugin_name = name or getattr(plugin_obj, "name", module_name.rsplit(".", 1)[-1])
        manifest = PluginManifest(
            name=plugin_name,
            version=getattr(plugin_obj, "version", "0.1.0"),
            description=getattr(plugin_obj, "description", ""),
            permissions=set(getattr(plugin_obj, "permissions", set())),
            entrypoint=entrypoint,
            tags=list(getattr(plugin_obj, "tags", [])),
        )
        self._manifests[plugin_name] = manifest
        for action_name in dir(plugin_obj):
            if action_name.startswith("_"):
                continue
            action = getattr(plugin_obj, action_name)
            if callable(action):
                self._handlers.setdefault(plugin_name, {})[action_name] = action
        if callable(plugin_obj):
            self._handlers.setdefault(plugin_name, {})["run"] = plugin_obj
        return manifest

    def call(self, name: str, action: str = "run", **kwargs) -> PluginResult:
        started = perf_counter()
        manifest = self._manifests.get(name)
        if manifest is None:
            return PluginResult(
                ok=False,
                plugin=name,
                action=action,
                error={"code": "PLUGIN_NOT_FOUND", "message": f"{name} is not registered."},
            )
        missing_permissions = sorted(set(manifest.permissions) - self._granted_permissions)
        if missing_permissions:
            return PluginResult(
                ok=False,
                plugin=name,
                action=action,
                error={
                    "code": "PLUGIN_PERMISSION_DENIED",
                    "message": "Plugin requires permissions that were not granted by the app.",
                    "missing_permissions": missing_permissions,
                    "hint": "Pass QuickAPI(..., plugin_permissions={...}) or call app.plugins.grant(...).",
                },
            )
        handler = self._handlers.get(name, {}).get(action)
        if handler is None:
            return PluginResult(
                ok=False,
                plugin=name,
                action=action,
                error={"code": "PLUGIN_ACTION_NOT_FOUND", "message": f"{name}.{action} is not registered."},
            )
        try:
            signature = inspect.signature(handler)
            if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
                data = handler(**kwargs)
            else:
                accepted = {key: value for key, value in kwargs.items() if key in signature.parameters}
                data = handler(**accepted)
            return PluginResult(True, name, action, data=data, duration_ms=round((perf_counter() - started) * 1000, 3))
        except Exception as exc:
            return PluginResult(
                False,
                name,
                action,
                error={"type": exc.__class__.__name__, "message": str(exc)},
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )

    def list(self) -> list[dict[str, Any]]:
        items = []
        for manifest in sorted(self._manifests.values(), key=lambda item: item.name):
            data = manifest.to_dict()
            data["granted"] = sorted(set(manifest.permissions) & self._granted_permissions)
            data["missing_permissions"] = sorted(set(manifest.permissions) - self._granted_permissions)
            items.append(data)
        return items

    def describe(self, name: str) -> dict[str, Any] | None:
        manifest = self._manifests.get(name)
        if manifest is None:
            return None
        data = manifest.to_dict()
        data["actions"] = sorted(self._handlers.get(name, {}))
        data["granted"] = sorted(set(manifest.permissions) & self._granted_permissions)
        data["missing_permissions"] = sorted(set(manifest.permissions) - self._granted_permissions)
        return data
