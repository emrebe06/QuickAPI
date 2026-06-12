from quickapi import q


def test_ok_response_shape():
    response = q.ok({"pong": True})

    assert response["ok"] is True
    assert response["status"] == 200
    assert response["code"] == "OK"
    assert response["data"] == {"pong": True}
    assert response["error"] is None
    assert response["meta"]["request_id"].startswith("req_")
    assert response["meta"]["engine"] == "quickapi"


def test_error_response_shape():
    response = q.error(422, "VALIDATION_ERROR", "product_id is required", {"field": "product_id"})

    assert response["ok"] is False
    assert response["status"] == 422
    assert response["code"] == "VALIDATION_ERROR"
    assert response["data"] is None
    assert response["error"]["detail"] == {"field": "product_id"}
