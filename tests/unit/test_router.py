from quickapi import QuickAPI, q


def test_get_route_registers_and_dispatches():
    app = QuickAPI("Test")

    @app.get("/ping")
    def ping():
        return q.ok({"pong": True})

    response = app.handle("GET", "/ping").to_dict()

    assert response["status"] == 200
    assert response["data"] == {"pong": True}


def test_post_route_receives_body():
    app = QuickAPI("Test")

    @app.post("/echo")
    def echo(body):
        return q.ok(body)

    response = app.handle("POST", "/echo", body={"hello": "world"}).to_dict()

    assert response["data"] == {"hello": "world"}


def test_unknown_route_returns_404():
    app = QuickAPI("Test")

    response = app.handle("GET", "/missing").to_dict()

    assert response["status"] == 404
    assert response["code"] == "NOT_FOUND"


def test_wrong_method_returns_405():
    app = QuickAPI("Test")

    @app.get("/ping")
    def ping():
        return q.ok()

    response = app.handle("POST", "/ping").to_dict()

    assert response["status"] == 405
    assert response["code"] == "METHOD_NOT_ALLOWED"


def test_path_wildcard_route_matches_nested_paths():
    app = QuickAPI("Test")

    @app.get("/static/{file_path:path}")
    def static_file(file_path):
        return q.ok({"file_path": file_path})

    response = app.handle("GET", "/static/images/logo.png").to_dict()

    assert response["status"] == 200
    assert response["data"] == {"file_path": "images/logo.png"}
