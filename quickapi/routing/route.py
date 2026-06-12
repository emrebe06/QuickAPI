import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Route:
    path: str
    method: str
    handler: Callable[..., Any]
    errors: list[int] = field(default_factory=list)
    ml_check: bool = False
    auth: bool = False
    rate_limit: str | None = None
    native: dict[str, str] | None = None
    name: str | None = None

    def __post_init__(self):
        self.method = self.method.upper()
        self.name = self.name or getattr(self.handler, "__name__", "native_endpoint")
        self._pattern, self._params = self._compile_path(self.path)

    def match(self, path: str) -> dict[str, str] | None:
        found = self._pattern.fullmatch(path)
        if not found:
            return None
        return found.groupdict()

    def describe(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "name": self.name,
            "errors": self.errors,
            "ml_check": self.ml_check,
            "auth": self.auth,
            "rate_limit": self.rate_limit,
            "native": bool(self.native),
        }

    @staticmethod
    def _compile_path(path: str):
        tokens = re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)(?::path)?}", path)
        pattern = re.escape(path)
        for param in tokens:
            wildcard = r"\{" + param + r":path\}"
            normal = r"\{" + param + r"\}"
            if wildcard in pattern:
                pattern = pattern.replace(wildcard, f"(?P<{param}>.+)")
            else:
                pattern = pattern.replace(normal, f"(?P<{param}>[^/]+)")
        return re.compile(pattern), tokens
