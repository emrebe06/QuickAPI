from time import time


class RateLimiter:
    PRESETS = {
        "default": (60, 60),
        "strict": (20, 60),
        "auth": (10, 60),
    }

    def __init__(self):
        self._buckets = {}

    def allow(self, key: str, preset: str = "default") -> bool:
        limit, window = self.PRESETS.get(preset, self.PRESETS["default"])
        now = time()
        bucket = [stamp for stamp in self._buckets.get(key, []) if now - stamp < window]
        if len(bucket) >= limit:
            self._buckets[key] = bucket
            return False
        bucket.append(now)
        self._buckets[key] = bucket
        return True
