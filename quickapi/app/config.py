from dataclasses import dataclass
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
    job_workers: int = 4
    native_library: str | None = None
    auth_tokens: set[str] | tuple[str, ...] | list[str] | None = None
    auth_validator: Callable[[str, Any], bool | dict] | None = None
