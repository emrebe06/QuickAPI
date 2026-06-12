import importlib
import importlib.util
import sys
from pathlib import Path


DEFAULT_APP_NAME = "app"


def load_app(target: str):
    module_target, app_name = split_target(target)
    if looks_like_file(module_target):
        return load_app_from_file(module_target, app_name)
    return load_app_from_module(module_target, app_name)


def split_target(target: str) -> tuple[str, str]:
    if ":" not in target:
        return target, DEFAULT_APP_NAME
    module_target, app_name = target.rsplit(":", 1)
    if not module_target or not app_name:
        raise RuntimeError("App target must look like 'module:app' or 'path/to/main.py:app'")
    return module_target, app_name


def looks_like_file(target: str) -> bool:
    return target.endswith(".py") or "\\" in target or "/" in target


def load_app_from_file(path: str, app_name: str = DEFAULT_APP_NAME):
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise RuntimeError(f"App file does not exist: {file_path}")
    spec = importlib.util.spec_from_file_location("quickapi_user_app", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return get_app(module, app_name, str(file_path))


def load_app_from_module(module_path: str, app_name: str = DEFAULT_APP_NAME):
    ensure_cwd_on_path()
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise RuntimeError(f"Cannot import module '{module_path}': {exc}") from exc
    return get_app(module, app_name, module_path)


def ensure_cwd_on_path():
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)


def get_app(module, app_name: str, source: str):
    app = getattr(module, app_name, None)
    if app is None:
        raise RuntimeError(f"{source} does not expose '{app_name}'")
    if not hasattr(app, "run") or not hasattr(app, "handle"):
        raise RuntimeError(f"{source}:{app_name} is not a QuickAPI application")
    return app
