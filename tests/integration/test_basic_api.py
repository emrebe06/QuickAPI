from examples.basic_api.main import app


def test_basic_api_ping():
    response = app.handle("GET", "/ping").to_dict()

    assert response["status"] == 200
    assert response["data"] == {"pong": True}


def test_basic_api_unknown():
    response = app.handle("GET", "/unknown").to_dict()

    assert response["status"] == 404


def test_docs_html_contains_try_console():
    response = app.handle("GET", "/docs")
    html = response.to_dict()

    assert response.status == 200
    assert "Send JSON Request" in html
    assert "200 OK" in html
    assert "result-error" in html
