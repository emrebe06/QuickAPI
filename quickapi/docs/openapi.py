from __future__ import annotations

from typing import Any

from quickapi.schema.generator import to_openapi_schema


def build_openapi(app) -> dict:
    paths = {}
    has_auth = False
    for route in app.routes:
        item = paths.setdefault(route.path, {})
        operation = {
            "summary": route.summary or route.name,
            "operationId": route.name,
            "tags": route.tags or ["default"],
            "parameters": [
                *_path_parameters(route),
                *_query_parameters(route),
            ],
            "responses": _responses(route),
            "x-quickapi": {
                "ml_check": route.ml_check,
                "auth": route.auth,
                "rate_limit": route.rate_limit,
                "native": bool(route.native),
            },
        }
        if route.description:
            operation["description"] = route.description
        if route.body_schema:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": to_openapi_schema(route.body_schema),
                        **_example_content(route, "body"),
                    }
                },
            }
        if route.response_schema:
            operation["responses"]["200"]["content"] = {
                "application/json": {"schema": to_openapi_schema(route.response_schema)}
            }
        if route.auth:
            has_auth = True
            operation["security"] = [{"BearerAuth": []}]
        item[route.method.lower()] = operation

    document = {
        "openapi": "3.1.0",
        "info": {"title": app.config.name, "version": "0.1.0"},
        "paths": paths,
    }
    if has_auth:
        document["components"] = {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "API token",
                }
            }
        }
    return document


def _responses(route) -> dict[str, Any]:
    responses = {
        "200": {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "ok": {"type": "boolean"},
                            "status": {"type": "integer"},
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                            "data": {"type": "object"},
                            "error": {"type": ["object", "null"]},
                            "meta": {"type": "object"},
                        },
                    }
                }
            },
        }
    }
    for code in sorted(set(route.errors or [400, 401, 403, 404, 422, 429, 500])):
        responses[str(code)] = {"description": "QuickAPI error response"}
    return responses


def _path_parameters(route) -> list[dict[str, Any]]:
    schema = route.path_schema or {}
    return [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": _field_schema(schema, name),
        }
        for name in getattr(route, "_params", [])
    ]


def _query_parameters(route) -> list[dict[str, Any]]:
    schema = route.query_schema or {}
    if not isinstance(schema, dict):
        return []
    parameters = []
    for name, rule in schema.items():
        parameters.append(
            {
                "name": name,
                "in": "query",
                "required": _is_required(rule),
                "schema": to_openapi_schema(_unwrap_rule(rule)),
            }
        )
    return parameters


def _field_schema(schema: dict, name: str) -> dict[str, Any]:
    if isinstance(schema, dict) and name in schema:
        return to_openapi_schema(_unwrap_rule(schema[name]))
    return {"type": "string"}


def _unwrap_rule(rule: Any) -> Any:
    if isinstance(rule, tuple) and rule:
        return rule[0]
    return rule


def _is_required(rule: Any) -> bool:
    if isinstance(rule, tuple):
        return False
    if isinstance(rule, dict):
        return bool(rule.get("required", True))
    return True


def _example_content(route, key: str) -> dict[str, Any]:
    if not route.examples:
        return {}
    value = route.examples.get(key)
    if value is None:
        value = route.examples.get("request")
    return {"example": value} if value is not None else {}
