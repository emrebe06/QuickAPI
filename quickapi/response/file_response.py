import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class FileResponse:
    path: str | Path
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    download_name: str | None = None
    chunk_size: int = 1024 * 256

    def __post_init__(self):
        self.path = Path(self.path)
        mime = mimetypes.guess_type(self.path.name)[0] or "application/octet-stream"
        self.headers.setdefault("Content-Type", mime)
        if self.path.exists():
            self.headers.setdefault("Content-Length", str(self.path.stat().st_size))
        if self.download_name:
            self.headers.setdefault("Content-Disposition", f'attachment; filename="{self.download_name}"')

    def to_dict(self):
        return self

    def iter_bytes(self) -> Iterator[bytes]:
        with self.path.open("rb") as handle:
            while True:
                chunk = handle.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    def to_bytes(self) -> bytes:
        return b"".join(self.iter_bytes())


def safe_file_response(root: str | Path, requested_path: str, *, download: bool = False) -> FileResponse | None:
    root_path = Path(root).resolve()
    clean_path = requested_path.replace("\\", "/").lstrip("/")
    target = (root_path / clean_path).resolve()
    if target == root_path or root_path not in target.parents or not target.is_file():
        return None
    return FileResponse(target, download_name=target.name if download else None)
