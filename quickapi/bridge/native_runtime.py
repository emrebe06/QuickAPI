import ctypes
import json
from pathlib import Path


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

    def _require(self):
        if not self.library:
            raise RuntimeError("Native runtime library is not loaded")
