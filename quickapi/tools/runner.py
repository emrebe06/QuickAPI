from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    duration_ms: float = 0.0
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class ToolRunner:
    def __init__(
        self,
        *,
        allow_shell: bool = False,
        allowed_bins: set[str] | list[str] | tuple[str, ...] | None = None,
        default_timeout: float = 30.0,
        workspace_root: str | Path | None = None,
    ):
        self.allow_shell = allow_shell
        self.allowed_bins = set(allowed_bins or {"ffmpeg", "ffprobe", "python", "node", "npm", "npx", "git"})
        self.default_timeout = default_timeout
        self.workspace_root = Path(workspace_root).expanduser().resolve() if workspace_root else None

    def run(self, command: list[str], *, cwd: str | Path | None = None, timeout: float | None = None) -> ToolResult:
        started = perf_counter()
        if not isinstance(command, list):
            return ToolResult(
                False,
                [],
                error={"code": "INVALID_COMMAND", "message": "Command must be a JSON list, for example ['ffmpeg', '-version']."},
            )
        if not command:
            return ToolResult(False, command, error={"code": "EMPTY_COMMAND", "message": "Command cannot be empty."})
        command = [str(part) for part in command]
        executable = Path(command[0]).name.lower().removesuffix(".exe")
        if executable not in {item.lower().removesuffix(".exe") for item in self.allowed_bins}:
            return ToolResult(
                False,
                command,
                error={
                    "code": "TOOL_NOT_ALLOWED",
                    "message": f"'{command[0]}' is not in the allowed tool list.",
                    "allowed_bins": sorted(self.allowed_bins),
                },
            )
        safe_cwd = self._resolve_cwd(cwd)
        if isinstance(safe_cwd, ToolResult):
            return safe_cwd
        try:
            proc = subprocess.run(
                command,
                cwd=str(safe_cwd) if safe_cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout or self.default_timeout,
                shell=False,
            )
            return ToolResult(
                proc.returncode == 0,
                command,
                stdout=proc.stdout[-20000:],
                stderr=proc.stderr[-20000:],
                returncode=proc.returncode,
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                False,
                command,
                stdout=(exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "",
                duration_ms=round((perf_counter() - started) * 1000, 3),
                error={"code": "TOOL_TIMEOUT", "message": f"Tool exceeded timeout {timeout or self.default_timeout}s."},
            )
        except Exception as exc:
            return ToolResult(
                False,
                command,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )

    def ffmpeg_convert(self, source: str | Path, target: str | Path, *, extra: list[str] | None = None, timeout: float = 300.0) -> ToolResult:
        source_path = self._resolve_workspace_file(source)
        target_path = self._resolve_workspace_file(target)
        if isinstance(source_path, ToolResult):
            return source_path
        if isinstance(target_path, ToolResult):
            return target_path
        command = ["ffmpeg", "-y", "-i", str(source_path), *(extra or []), str(target_path)]
        return self.run(command, timeout=timeout)

    def _resolve_cwd(self, cwd: str | Path | None) -> Path | None | ToolResult:
        if cwd is None:
            return self.workspace_root
        resolved = Path(cwd).expanduser().resolve()
        if self.workspace_root is None:
            return resolved
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return ToolResult(
                False,
                [],
                error={
                    "code": "CWD_OUTSIDE_WORKSPACE",
                    "message": "Tool cwd is outside the configured workspace root.",
                    "workspace_root": str(self.workspace_root),
                    "cwd": str(resolved),
                },
            )
        return resolved

    def _resolve_workspace_file(self, path: str | Path) -> Path | ToolResult:
        if self.workspace_root is None:
            return Path(path).expanduser().resolve()
        candidate = Path(path)
        resolved = (self.workspace_root / candidate).resolve() if not candidate.is_absolute() else candidate.expanduser().resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return ToolResult(
                False,
                [],
                error={
                    "code": "PATH_OUTSIDE_WORKSPACE",
                    "message": "Tool file path is outside the configured workspace root.",
                    "workspace_root": str(self.workspace_root),
                    "path": str(resolved),
                },
            )
        return resolved
