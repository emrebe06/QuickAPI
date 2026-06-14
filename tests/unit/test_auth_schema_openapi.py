from quickapi import QuickAPI, q


def test_auth_route_requires_bearer_token():
    app = QuickAPI("Auth API", auth_tokens={"secret"})

    @app.get("/admin", auth=True)
    def admin():
        return q.ok({"admin": True})

    response = app.handle("GET", "/admin").to_dict()

    assert response["status"] == 401
    assert response["error"]["detail"]["where"] == "headers.Authorization"


def test_auth_route_rejects_invalid_token():
    app = QuickAPI("Auth API", auth_tokens={"secret"})

    @app.get("/admin", auth=True)
    def admin():
        return q.ok({"admin": True})

    response = app.handle("GET", "/admin", headers={"Authorization": "Bearer wrong"}).to_dict()

    assert response["status"] == 403
    assert response["code"] == "FORBIDDEN"


def test_auth_route_injects_auth_context():
    app = QuickAPI("Auth API", auth_tokens={"secret"})

    @app.get("/me", auth=True)
    def me(auth):
        return q.ok({"method": auth["method"]})

    response = app.handle("GET", "/me", headers={"Authorization": "Bearer secret"}).to_dict()

    assert response["status"] == 200
    assert response["data"] == {"method": "bearer"}


def test_route_body_query_and_path_validation():
    app = QuickAPI("Schema API")

    @app.post(
        "/products/{product_id}",
        path_schema={"product_id": str},
        query_schema={"dry_run": (bool,)},
        body_schema={
            "name": {"type": "string", "min_length": 3},
            "price": {"type": "number", "minimum": 1},
            "tags": [str],
        },
    )
    def update(product_id, body, query):
        return q.ok({"product_id": product_id, "body": body, "query": query})

    response = app.handle(
        "POST",
        "/products/abc",
        query={"dry_run": "yes"},
        body={"name": "ab", "price": 0, "tags": ["coffee", 42]},
    ).to_dict()

    assert response["status"] == 422
    issues = response["error"]["detail"]["issues"]
    wheres = {issue["where"] for issue in issues}
    assert "query.dry_run" in wheres
    assert "body.name" in wheres
    assert "body.price" in wheres
    assert "body.tags[1]" in wheres


def test_openapi_includes_auth_parameters_and_request_body_schema():
    app = QuickAPI("OpenAPI API", auth_tokens={"secret"})

    @app.post(
        "/products/{product_id}",
        auth=True,
        tags=["products"],
        summary="Update product",
        path_schema={"product_id": str},
        query_schema={"dry_run": (bool,)},
        body_schema={"name": str, "price": {"type": "number", "minimum": 1}},
        response_schema={"updated": bool},
        errors=[401, 403, 422],
    )
    def update():
        return q.ok({"updated": True})

    document = app.handle("GET", "/openapi.json").to_dict()["data"]
    operation = document["paths"]["/products/{product_id}"]["post"]

    assert operation["summary"] == "Update product"
    assert operation["security"] == [{"BearerAuth": []}]
    assert document["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert operation["parameters"][0]["name"] == "product_id"
    assert operation["parameters"][1]["name"] == "dry_run"
    assert operation["requestBody"]["content"]["application/json"]["schema"]["required"] == ["name", "price"]
    assert "200" in operation["responses"]
    assert "422" in operation["responses"]
