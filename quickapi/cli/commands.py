import subprocess
import sys
import textwrap
from pathlib import Path
from time import perf_counter
from time import sleep

from quickapi.cli.loader import load_app


def dev(path: str, host: str = "127.0.0.1", port: int = 8080, access_log: bool = True):
    run(path, host=host, port=port, access_log=access_log)


def run(
    target: str,
    host: str = "0.0.0.0",
    port: int = 8000,
    access_log: bool = True,
    reload: bool = False,
):
    if reload:
        return run_with_reload(target, host=host, port=port, access_log=access_log)
    app = load_app(target)
    print_startup(target, host, port, access_log, reload=False)
    app.run(host=host, port=port, access_log=access_log)


def serve(target: str, host: str = "0.0.0.0", port: int = 8000, access_log: bool = True, reload: bool = False):
    return run(target, host=host, port=port, access_log=access_log, reload=reload)


def routes(target: str = "examples/basic_api/main.py"):
    app = load_app(target)
    for route in app.routes:
        meta = route.describe()
        flags = []
        if meta["ml_check"]:
            flags.append("ml")
        if meta["auth"]:
            flags.append("auth")
        if meta["rate_limit"]:
            flags.append(f"rate={meta['rate_limit']}")
        if meta["native"]:
            flags.append("native")
        suffix = f" [{' '.join(flags)}]" if flags else ""
        errors = ",".join(str(code) for code in meta["errors"]) or "-"
        print(f"{route.method:6} {route.path:28} {route.name:20} errors={errors}{suffix}")


def docs(target: str = "examples/basic_api/main.py", host: str = "127.0.0.1", port: int = 8080, access_log: bool = True):
    app = load_app(target)
    print(f"Docs: http://{host}:{port}/docs")
    app.run(host=host, port=port, access_log=access_log)


def bench(target: str = "examples/basic_api/main.py", route_path: str = "/ping", iterations: int = 1000):
    app = load_app(target)
    start = perf_counter()
    for _ in range(iterations):
        app.handle("GET", route_path)
    elapsed = (perf_counter() - start) * 1000
    print(f"{iterations} requests in {elapsed:.2f} ms ({iterations / (elapsed / 1000):.0f} req/s)")


def new(name: str):
    root = Path(name)
    root.mkdir(parents=True, exist_ok=False)
    (root / "main.py").write_text(
        textwrap.dedent(
            f'''\
            from quickapi import QuickAPI, q

            app = QuickAPI("{name}", docs=True)


            @app.get("/health")
            def health():
                return q.ok({{"status": "running"}})


            @app.get("/ping")
            def ping():
                return q.ok({{"pong": True}})


            @app.post("/echo")
            def echo(body, request):
                return q.ok({{
                    "body": body,
                    "ip": request.ip,
                    "request_id": request.request_id,
                }})


            if __name__ == "__main__":
                app.run(host="127.0.0.1", port=8080)
            '''
        ),
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("quickapi\n", encoding="utf-8")
    (root / "README.md").write_text(
        f"# {name}\n\n"
        "Run locally:\n\n"
        "```bash\n"
        "quickapi run main:app --host 0.0.0.0 --port 8000\n"
        "```\n\n"
        "Behind nginx, bind to localhost and proxy to `http://127.0.0.1:8080`.\n",
        encoding="utf-8",
    )
    print(f"Created {root}")


def print_startup(target: str, host: str, port: int, access_log: bool, reload: bool):
    print("QuickAPI runtime")
    print(f"  app:        {target}")
    print(f"  listen:     http://{host}:{port}")
    print(f"  docs:       http://{host}:{port}/docs")
    print(f"  access log: {'on' if access_log else 'off'}")
    print(f"  reload:     {'on' if reload else 'off'}")


def run_with_reload(target: str, host: str, port: int, access_log: bool):
    print_startup(target, host, port, access_log, reload=True)
    watched = watched_files(target)
    child = None
    last = snapshot(watched)
    try:
        while True:
            if child is None or child.poll() is not None:
                child = start_child(target, host, port, access_log)
            sleep(1)
            current = snapshot(watched)
            if current != last:
                print("[quickapi] reload: Python file change detected", flush=True)
                stop_child(child)
                child = start_child(target, host, port, access_log)
                last = current
    except KeyboardInterrupt:
        if child is not None:
            stop_child(child)


def start_child(target: str, host: str, port: int, access_log: bool):
    args = [
        sys.executable,
        "-m",
        "quickapi.cli.main",
        "run",
        target,
        "--host",
        host,
        "--port",
        str(port),
    ]
    if not access_log:
        args.append("--no-access-log")
    return subprocess.Popen(args)


def stop_child(child):
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()


def watched_files(target: str) -> list[Path]:
    if target.endswith(".py") or "/" in target or "\\" in target:
        return [Path(target.split(":", 1)[0]).resolve()]
    return sorted(Path.cwd().glob("**/*.py"))


def snapshot(paths: list[Path]) -> dict[str, float]:
    values = {}
    for path in paths:
        try:
            values[str(path)] = path.stat().st_mtime
        except OSError:
            values[str(path)] = 0
    return values
