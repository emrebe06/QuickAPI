from pathlib import Path

from quickapi import QuickAPI
from quickapi.response.file_response import FileResponse, safe_file_response


def test_file_response_streams_chunks(tmp_path: Path):
    path = tmp_path / "large.txt"
    path.write_bytes(b"a" * 600_000)
    response = FileResponse(path, chunk_size=128_000)

    chunks = list(response.iter_bytes())

    assert response.headers["Content-Length"] == "600000"
    assert len(chunks) > 1
    assert sum(len(chunk) for chunk in chunks) == 600_000


def test_static_file_helper_blocks_traversal(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "ok.txt").write_text("ok", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    assert safe_file_response(root, "ok.txt") is not None
    assert safe_file_response(root, "../secret.txt") is None


def test_app_static_file_returns_file_response(tmp_path: Path):
    root = tmp_path / "public"
    root.mkdir()
    (root / "ok.txt").write_text("ok", encoding="utf-8")
    app = QuickAPI()

    response = app.static_file(root, "ok.txt")

    assert isinstance(response, FileResponse)
    assert b"".join(response.iter_bytes()) == b"ok"
