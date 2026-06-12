from quickapi import q
from quickapi.http.request import Request
from quickapi.security.guard import SecurityGuard


def test_validation_helper():
    response = q.validation("Invalid quantity", {"quantity": 0})

    assert response["status"] == 422
    assert response["code"] == "VALIDATION_ERROR"


def test_rate_limit_helper():
    response = q.too_many_requests()

    assert response["status"] == 429
    assert response["code"] == "TOO_MANY_REQUESTS"


def test_server_error_helper():
    response = q.server_error(detail="boom")

    assert response["status"] == 500
    assert response["error"]["detail"] == "boom"


def test_security_guard_rejects_suspicious_path():
    guard = SecurityGuard(enabled=True)
    request = Request.build("GET", "/static/../secret.txt")

    response = guard.check(request)

    assert response["status"] == 400
    assert response["error"]["detail"]["where"] == "path"


def test_security_guard_explains_wrong_content_type():
    guard = SecurityGuard(enabled=True)
    request = Request.build(
        "POST",
        "/api/products",
        raw_body=b'{"x":1}',
        headers={"Content-Type": "text/plain"},
    )

    response = guard.check(request)

    assert response["status"] == 415
    assert response["error"]["detail"]["where"] == "headers.Content-Type"
