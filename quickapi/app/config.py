from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any


@dataclass
class QuickAPIConfig:
    name: str = "QuickAPI"
    secure: bool = False
    ml: bool = False
    docs: bool = True
    docs_logo_url: str | None = None
    docs_favicon_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8080
    max_body_size: int = 1024 * 1024
    max_in_flight: int = 512
    overload_status: int = 503
    request_timeout_seconds: float = 15.0
    json_stream_threshold: int = 256 * 1024
    job_workers: int = 4
    job_max_pending: int = 1024
    native_library: str | None = None
    synaptic: bool = False
    ml_guard: bool = False
    ml_guard_block: bool = True
    ml_guard_strict_validation: bool = True
    ml_guard_max_string_length: int = 4096
    ml_guard_max_array_length: int = 1000
    ml_guard_max_object_keys: int = 250
    plugins_enabled: bool = True
    plugin_permissions: set[str] | tuple[str, ...] | list[str] | None = None
    llm_gateway_enabled: bool = True
    local_tools_enabled: bool = False
    local_tools_root: str | Path | None = None
    local_tools_allowed_bins: set[str] | tuple[str, ...] | list[str] | None = None
    local_tools_timeout: float = 30.0
    webhooks_enabled: bool = True
    agent_backend_enabled: bool = False
    auth_tokens: set[str] | tuple[str, ...] | list[str] | None = None
    auth_validator: Callable[[str, Any], bool | dict] | None = None
