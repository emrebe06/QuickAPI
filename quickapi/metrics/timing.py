from contextlib import contextmanager
from time import perf_counter


def elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


@contextmanager
def timer():
    start = perf_counter()
    yield lambda: elapsed_ms(start)
