from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol


@dataclass
class LLMResponse:
    ok: bool
    provider: str
    model: str
    content: str = ""
    raw: Any = None
    duration_ms: float = 0.0
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "raw": self.raw,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class LLMProvider(Protocol):
    name: str

    def complete(self, messages: list[dict[str, str]], *, model: str, **kwargs) -> LLMResponse:
        ...


class EchoProvider:
    name = "echo"

    def complete(self, messages: list[dict[str, str]], *, model: str = "echo-local", **kwargs) -> LLMResponse:
        started = perf_counter()
        content = "\n".join(item.get("content", "") for item in messages if item.get("role") != "system")
        return LLMResponse(True, self.name, model, content=content, raw={"messages": messages}, duration_ms=round((perf_counter() - started) * 1000, 3))


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key_env: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env

    def complete(self, messages: list[dict[str, str]], *, model: str, **kwargs) -> LLMResponse:
        started = perf_counter()
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            return LLMResponse(False, self.name, model, error={"code": "MISSING_API_KEY", "env": self.api_key_env})
        body = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 512),
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=float(kwargs.get("timeout", 30.0))) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return LLMResponse(True, self.name, model, content=content, raw=payload, duration_ms=round((perf_counter() - started) * 1000, 3))
        except Exception as exc:
            return LLMResponse(False, self.name, model, error={"type": exc.__class__.__name__, "message": str(exc)}, duration_ms=round((perf_counter() - started) * 1000, 3))


class LLMGateway:
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {"echo": EchoProvider()}

    def register(self, provider: LLMProvider):
        self._providers[provider.name] = provider
        return provider

    def register_openai_compatible(self, name: str, base_url: str, api_key_env: str = "OPENAI_API_KEY"):
        return self.register(OpenAICompatibleProvider(name, base_url, api_key_env))

    def complete(self, messages: list[dict[str, str]], *, provider: str = "echo", model: str = "echo-local", **kwargs) -> LLMResponse:
        selected = self._providers.get(provider)
        if selected is None:
            return LLMResponse(False, provider, model, error={"code": "LLM_PROVIDER_NOT_FOUND", "available": sorted(self._providers)})
        return selected.complete(messages, model=model, **kwargs)

    def list(self) -> list[dict[str, str]]:
        return [{"name": name, "type": provider.__class__.__name__} for name, provider in sorted(self._providers.items())]
