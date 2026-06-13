import ctypes
import json
from pathlib import Path


class NativeResult(ctypes.Structure):
    _fields_ = [
        ("ok", ctypes.c_int),
        ("code", ctypes.c_int),
        ("value", ctypes.c_size_t),
        ("message", ctypes.c_char_p),
    ]


class NativeStringView(ctypes.Structure):
    _fields_ = [("data", ctypes.c_char_p), ("size", ctypes.c_size_t)]


class NativeRequestView(ctypes.Structure):
    _fields_ = [
        ("method", NativeStringView),
        ("path", NativeStringView),
        ("query", NativeStringView),
        ("body", NativeStringView),
        ("ip", NativeStringView),
    ]


class NativeIsolateSpec(ctypes.Structure):
    _fields_ = [
        ("executable", ctypes.c_char_p),
        ("working_directory", ctypes.c_char_p),
        ("timeout_ms", ctypes.c_uint),
        ("memory_limit_mb", ctypes.c_uint),
    ]


class NativeRuntime:
    def __init__(self, library: str | None = None):
        self.library_path = library
        self.library = ctypes.CDLL(str(Path(library).expanduser())) if library else None

    @property
    def available(self) -> bool:
        return self.library is not None

    def core_name(self) -> str | None:
        if not self.library:
            return None
        self.library.quickapi_core_name.restype = ctypes.c_char_p
        return self.library.quickapi_core_name().decode("utf-8")

    def version(self) -> str | None:
        if not self.library:
            return None
        self.library.quickapi_core_version.restype = ctypes.c_char_p
        return self.library.quickapi_core_version().decode("utf-8")

    def ok(self, data=None, status: int = 200, code: str = "OK", message: str = "Success") -> dict:
        self._require()
        self.library.quickapi_json_ok.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_json_ok.restype = ctypes.c_char_p
        raw = self.library.quickapi_json_ok(
            status,
            code.encode("utf-8"),
            message.encode("utf-8"),
            json.dumps(data).encode("utf-8"),
        )
        return json.loads(raw.decode("utf-8"))

    def writer_ok(self, data=None, status: int = 200, code: str = "OK", message: str = "Success") -> dict:
        self._require()
        self.library.quickapi_json_writer_success.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_json_writer_success.restype = ctypes.c_char_p
        raw = self.library.quickapi_json_writer_success(
            status,
            code.encode("utf-8"),
            message.encode("utf-8"),
            json.dumps(data).encode("utf-8"),
        )
        return json.loads(raw.decode("utf-8"))

    def payload_risk_score(self, path: str, payload: str) -> float:
        self._require()
        self.library.quickapi_security_payload_risk_score.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_security_payload_risk_score.restype = ctypes.c_double
        return float(self.library.quickapi_security_payload_risk_score(path.encode("utf-8"), payload.encode("utf-8")))

    def payload_feature_count(self, payload: str) -> int:
        self._require()
        self.library.quickapi_security_payload_feature_count.argtypes = [ctypes.c_char_p]
        self.library.quickapi_security_payload_feature_count.restype = ctypes.c_uint
        return int(self.library.quickapi_security_payload_feature_count(payload.encode("utf-8")))

    def fingerprint(self, path: str, payload: str) -> int:
        self._require()
        self.library.quickapi_security_fingerprint.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_security_fingerprint.restype = ctypes.c_ulonglong
        return int(self.library.quickapi_security_fingerprint(path.encode("utf-8"), payload.encode("utf-8")))

    def result_code_name(self, code: int) -> str:
        self._require()
        self.library.quickapi_result_code_name.argtypes = [ctypes.c_int]
        self.library.quickapi_result_code_name.restype = ctypes.c_char_p
        return self.library.quickapi_result_code_name(code).decode("utf-8")

    def arena_smoke(self, capacity: int = 1024) -> dict:
        self._require()
        self.library.quickapi_arena_create.argtypes = [ctypes.c_size_t]
        self.library.quickapi_arena_create.restype = ctypes.c_void_p
        self.library.quickapi_arena_alloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
        self.library.quickapi_arena_alloc.restype = NativeResult
        self.library.quickapi_arena_used.argtypes = [ctypes.c_void_p]
        self.library.quickapi_arena_used.restype = ctypes.c_size_t
        self.library.quickapi_arena_destroy.argtypes = [ctypes.c_void_p]
        arena = self.library.quickapi_arena_create(capacity)
        if not arena:
            return {"ok": False, "error": "arena_create_failed"}
        first = self.library.quickapi_arena_alloc(arena, 64, 8)
        second = self.library.quickapi_arena_alloc(arena, 128, 16)
        used = int(self.library.quickapi_arena_used(arena))
        self.library.quickapi_arena_destroy(arena)
        return {"ok": bool(first.ok and second.ok), "first_offset": int(first.value), "second_offset": int(second.value), "used": used}

    def buffer_smoke(self, text: str = "quickapi") -> dict:
        self._require()
        self.library.quickapi_buffer_create.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
        self.library.quickapi_buffer_create.restype = ctypes.c_void_p
        self.library.quickapi_buffer_append_cstr.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.library.quickapi_buffer_append_cstr.restype = NativeResult
        self.library.quickapi_buffer_data.argtypes = [ctypes.c_void_p]
        self.library.quickapi_buffer_data.restype = ctypes.c_char_p
        self.library.quickapi_buffer_size.argtypes = [ctypes.c_void_p]
        self.library.quickapi_buffer_size.restype = ctypes.c_size_t
        self.library.quickapi_buffer_destroy.argtypes = [ctypes.c_void_p]
        buffer = self.library.quickapi_buffer_create(8, 1024)
        if not buffer:
            return {"ok": False, "error": "buffer_create_failed"}
        result = self.library.quickapi_buffer_append_cstr(buffer, text.encode("utf-8"))
        data = self.library.quickapi_buffer_data(buffer).decode("utf-8")
        size = int(self.library.quickapi_buffer_size(buffer))
        self.library.quickapi_buffer_destroy(buffer)
        return {"ok": bool(result.ok), "data": data, "size": size}

    def job_queue_smoke(self) -> dict:
        self._require()
        self.library.quickapi_job_queue_create.argtypes = [ctypes.c_size_t]
        self.library.quickapi_job_queue_create.restype = ctypes.c_void_p
        self.library.quickapi_job_queue_push.argtypes = [ctypes.c_void_p, ctypes.c_ulonglong]
        self.library.quickapi_job_queue_push.restype = NativeResult
        self.library.quickapi_job_queue_pop.argtypes = [ctypes.c_void_p]
        self.library.quickapi_job_queue_pop.restype = NativeResult
        self.library.quickapi_job_queue_size.argtypes = [ctypes.c_void_p]
        self.library.quickapi_job_queue_size.restype = ctypes.c_size_t
        self.library.quickapi_job_queue_destroy.argtypes = [ctypes.c_void_p]
        queue = self.library.quickapi_job_queue_create(4)
        if not queue:
            return {"ok": False, "error": "queue_create_failed"}
        pushed = self.library.quickapi_job_queue_push(queue, 42)
        popped = self.library.quickapi_job_queue_pop(queue)
        size = int(self.library.quickapi_job_queue_size(queue))
        self.library.quickapi_job_queue_destroy(queue)
        return {"ok": bool(pushed.ok and popped.ok), "popped": int(popped.value), "size": size}

    def file_stream_smoke(self, path: str, chunk_size: int = 1024 * 64) -> dict:
        self._require()
        self.library.quickapi_file_stream_open.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        self.library.quickapi_file_stream_open.restype = ctypes.c_void_p
        self.library.quickapi_file_stream_read.argtypes = [ctypes.c_void_p]
        self.library.quickapi_file_stream_read.restype = NativeResult
        self.library.quickapi_file_stream_total_read.argtypes = [ctypes.c_void_p]
        self.library.quickapi_file_stream_total_read.restype = ctypes.c_ulonglong
        self.library.quickapi_file_stream_close.argtypes = [ctypes.c_void_p]
        stream = self.library.quickapi_file_stream_open(str(Path(path)).encode("utf-8"), chunk_size)
        if not stream:
            return {"ok": False, "error": "file_stream_open_failed"}
        reads = 0
        while True:
            result = self.library.quickapi_file_stream_read(stream)
            if not result.ok:
                message = result.message.decode("utf-8") if result.message else "read_failed"
                self.library.quickapi_file_stream_close(stream)
                return {"ok": False, "error": message}
            reads += 1
            if int(result.value) == 0:
                break
        total = int(self.library.quickapi_file_stream_total_read(stream))
        self.library.quickapi_file_stream_close(stream)
        return {"ok": True, "total_read": total, "reads": reads}

    def request_view_smoke(self, method: str = "GET", path: str = "/api/products") -> dict:
        self._require()
        self.library.quickapi_request_view_make.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_request_view_make.restype = NativeRequestView
        self.library.quickapi_request_view_valid.argtypes = [NativeRequestView]
        self.library.quickapi_request_view_valid.restype = ctypes.c_int
        self.library.quickapi_request_view_path_depth.argtypes = [NativeRequestView]
        self.library.quickapi_request_view_path_depth.restype = ctypes.c_size_t
        method_bytes = method.encode("utf-8")
        path_bytes = path.encode("utf-8")
        query_bytes = b""
        body_bytes = b""
        ip_bytes = b"127.0.0.1"
        view = self.library.quickapi_request_view_make(
            method_bytes,
            path_bytes,
            query_bytes,
            body_bytes,
            ip_bytes,
        )
        return {
            "ok": bool(self.library.quickapi_request_view_valid(view)),
            "path_depth": int(self.library.quickapi_request_view_path_depth(view)),
        }

    def response_writer_smoke(self) -> dict:
        self._require()
        self.library.quickapi_response_writer_create.argtypes = [ctypes.c_size_t]
        self.library.quickapi_response_writer_create.restype = ctypes.c_void_p
        self.library.quickapi_response_writer_status.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.library.quickapi_response_writer_status.restype = NativeResult
        self.library.quickapi_response_writer_header.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_response_writer_header.restype = NativeResult
        self.library.quickapi_response_writer_body.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        self.library.quickapi_response_writer_body.restype = NativeResult
        self.library.quickapi_response_writer_data.argtypes = [ctypes.c_void_p]
        self.library.quickapi_response_writer_data.restype = ctypes.c_char_p
        self.library.quickapi_response_writer_size.argtypes = [ctypes.c_void_p]
        self.library.quickapi_response_writer_size.restype = ctypes.c_size_t
        self.library.quickapi_response_writer_destroy.argtypes = [ctypes.c_void_p]
        writer = self.library.quickapi_response_writer_create(4096)
        if not writer:
            return {"ok": False, "error": "response_writer_create_failed"}
        status = self.library.quickapi_response_writer_status(writer, 200)
        header = self.library.quickapi_response_writer_header(writer, b"Content-Type", b"application/json")
        body = self.library.quickapi_response_writer_body(writer, b"{\"ok\":true}", len(b"{\"ok\":true}"))
        data = self.library.quickapi_response_writer_data(writer).decode("utf-8")
        size = int(self.library.quickapi_response_writer_size(writer))
        self.library.quickapi_response_writer_destroy(writer)
        return {"ok": bool(status.ok and header.ok and body.ok), "size": size, "has_status": data.startswith("HTTP/1.1 200")}

    def route_match_smoke(self) -> dict:
        self._require()
        self.library.quickapi_router_create.restype = ctypes.c_void_p
        self.library.quickapi_router_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_router_add.restype = ctypes.c_int
        self.library.quickapi_router_match.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_router_match.restype = ctypes.c_char_p
        self.library.quickapi_router_match_score.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_router_match_score.restype = ctypes.c_int
        self.library.quickapi_router_params.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.library.quickapi_router_params.restype = ctypes.c_char_p
        self.library.quickapi_router_destroy.argtypes = [ctypes.c_void_p]
        router = self.library.quickapi_router_create()
        if not router:
            return {"ok": False, "error": "router_create_failed"}
        self.library.quickapi_router_add(router, b"GET", b"/products/{id}", b"product_detail")
        self.library.quickapi_router_add(router, b"GET", b"/assets/{file_path:path}", b"asset_stream")
        handler = self.library.quickapi_router_match(router, b"GET", b"/products/42")
        score = int(self.library.quickapi_router_match_score(router, b"GET", b"/products/42"))
        params = json.loads(self.library.quickapi_router_params(router, b"GET", b"/products/42").decode("utf-8"))
        stream_handler = self.library.quickapi_router_match(router, b"GET", b"/assets/images/logo.png")
        self.library.quickapi_router_destroy(router)
        return {
            "ok": handler == b"product_detail" and stream_handler == b"asset_stream" and params.get("id") == "42",
            "handler": handler.decode("utf-8") if handler else None,
            "score": score,
            "params": params,
        }

    def security_scan_smoke(self) -> dict:
        self._require()
        self.library.quickapi_security_scan_request.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_char_p,
        ]
        self.library.quickapi_security_scan_request.restype = ctypes.c_char_p
        raw = self.library.quickapi_security_scan_request(
            b"POST",
            b"/checkout",
            b"application/json",
            len(b"{\"note\":\"drop table users\"}"),
            1024 * 1024,
            b"{\"note\":\"drop table users\"}",
        )
        return json.loads(raw.decode("utf-8"))

    def isolate_plan(self, executable: str = "worker", working_directory: str = ".", timeout_ms: int = 1000, memory_limit_mb: int = 128) -> dict:
        self._require()
        self.library.quickapi_isolate_plan.argtypes = [NativeIsolateSpec]
        self.library.quickapi_isolate_plan.restype = ctypes.c_char_p
        spec = NativeIsolateSpec(
            executable.encode("utf-8"),
            working_directory.encode("utf-8"),
            timeout_ms,
            memory_limit_mb,
        )
        return json.loads(self.library.quickapi_isolate_plan(spec).decode("utf-8"))

    def runtime_summary(self) -> dict:
        if not self.available:
            return {"native": False}
        return {
            "native": True,
            "core": self.core_name(),
            "version": self.version(),
            "features": {
                "arena": self.arena_smoke()["ok"],
                "buffer": self.buffer_smoke()["ok"],
                "job_queue": self.job_queue_smoke()["ok"],
                "json_writer": self.writer_ok({"native": True})["ok"] is True,
                "file_streamer": True,
                "request_view": self.request_view_smoke()["ok"],
                "response_writer": self.response_writer_smoke()["ok"],
                "route_matcher": self.route_match_smoke()["ok"],
                "request_scanner": self.security_scan_smoke()["allowed"] is False,
                "isolate_plan": self.isolate_plan()["valid"] is True,
                "security_hotpath": self.payload_feature_count("drop table") >= 1,
            },
        }

    def _require(self):
        if not self.library:
            raise RuntimeError("Native runtime library is not loaded")
