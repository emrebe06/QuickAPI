class Headers(dict):
    def __init__(self, values=None):
        super().__init__()
        for key, value in (values or {}).items():
            self[key] = value

    def __setitem__(self, key, value):
        super().__setitem__(self._normalize(key), value)

    def __getitem__(self, key):
        return super().__getitem__(self._normalize(key))

    def get(self, key, default=None):
        return super().get(self._normalize(key), default)

    @staticmethod
    def _normalize(key):
        return "-".join(part.capitalize() for part in str(key).split("-"))


def normalize_headers(headers) -> Headers:
    return Headers(headers or {})
