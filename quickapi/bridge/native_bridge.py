import ctypes
import json
from pathlib import Path


class NativeBridge:
    def __init__(self):
        self._libraries = {}

    def load(self, library: str):
        path = str(Path(library).expanduser())
        if path not in self._libraries:
            self._libraries[path] = ctypes.CDLL(path)
        return self._libraries[path]

    def call(self, library: str, symbol: str, payload) -> dict:
        lib = self.load(library)
        func = getattr(lib, symbol)
        func.argtypes = [ctypes.c_char_p]
        func.restype = ctypes.c_char_p
        raw = json.dumps(payload).encode("utf-8")
        result = func(raw)
        if result is None:
            return {}
        return json.loads(result.decode("utf-8"))

    def make_handler(self, library: str, symbol: str):
        def handler(body=None):
            return self.call(library, symbol, body or {})

        handler.__name__ = symbol
        return handler
