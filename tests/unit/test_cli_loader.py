from pathlib import Path

from quickapi.cli.loader import load_app, split_target


def test_split_target_defaults_to_app():
    assert split_target("main.py") == ("main.py", "app")


def test_split_target_module_app():
    assert split_target("examples.basic_api.main:app") == ("examples.basic_api.main", "app")


def test_load_app_from_file_target():
    app = load_app("examples/basic_api/main.py:app")

    response = app.handle("GET", "/ping").to_dict()

    assert response["status"] == 200


def test_load_app_from_module_target():
    app = load_app("examples.basic_api.main:app")

    response = app.handle("GET", "/ping").to_dict()

    assert response["data"] == {"pong": True}


def test_load_app_from_temp_file(tmp_path: Path):
    app_file = tmp_path / "main.py"
    app_file.write_text(
        "from quickapi import QuickAPI, q\n"
        "api = QuickAPI('Temp')\n"
        "@api.get('/ok')\n"
        "def ok():\n"
        "    return q.ok({'ok': True})\n",
        encoding="utf-8",
    )

    app = load_app(f"{app_file}:api")

    assert app.handle("GET", "/ok").to_dict()["status"] == 200
