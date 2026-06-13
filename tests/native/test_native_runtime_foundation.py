from pathlib import Path

import pytest

from quickapi.bridge.native_runtime import NativeRuntime


def native_library():
    candidates = [
        Path("build/native/Release/quickapi_native.dll"),
        Path("build/native/quickapi_native.dll"),
        Path("build/native/libquickapi_native.so"),
        Path("build/native/libquickapi_native.dylib"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


@pytest.fixture()
def runtime():
    library = native_library()
    if library is None:
        pytest.skip("native library is not built")
    return NativeRuntime(str(library))


def test_native_arena_buffer_and_job_queue(runtime):
    arena = runtime.arena_smoke(512)
    buffer = runtime.buffer_smoke("quickapi")
    queue = runtime.job_queue_smoke()

    assert arena["ok"] is True
    assert arena["used"] >= 192
    assert buffer == {"ok": True, "data": "quickapi", "size": 8}
    assert queue == {"ok": True, "popped": 42, "size": 0}


def test_native_runtime_summary(runtime):
    summary = runtime.runtime_summary()

    assert summary["native"] is True
    assert summary["features"]["arena"] is True
    assert summary["features"]["buffer"] is True
    assert summary["features"]["job_queue"] is True
    assert summary["features"]["json_writer"] is True
    assert summary["features"]["route_matcher"] is True
    assert summary["features"]["request_scanner"] is True
    assert summary["features"]["security_hotpath"] is True


def test_native_json_writer_and_file_stream(runtime, tmp_path):
    file_path = tmp_path / "payload.bin"
    file_path.write_bytes(b"x" * 150_000)

    payload = runtime.writer_ok({"hello": "native"})
    stream = runtime.file_stream_smoke(str(file_path), chunk_size=32_000)

    assert payload["ok"] is True
    assert payload["data"] == {"hello": "native"}
    assert stream["ok"] is True
    assert stream["total_read"] == 150_000
    assert stream["reads"] > 1


def test_native_request_response_and_isolate_primitives(runtime):
    request = runtime.request_view_smoke("POST", "/api/orders/create")
    response = runtime.response_writer_smoke()
    route = runtime.route_match_smoke()
    scan = runtime.security_scan_smoke()
    isolate = runtime.isolate_plan("worker", ".", 1500, 256)

    assert request == {"ok": True, "path_depth": 3}
    assert response["ok"] is True
    assert response["has_status"] is True
    assert route["ok"] is True
    assert route["params"] == {"id": "42"}
    assert scan["allowed"] is False
    assert "suspicious_payload" in scan["reasons"]
    assert isolate["valid"] is True
    assert isolate["mode"] == "planned_isolated_worker"
