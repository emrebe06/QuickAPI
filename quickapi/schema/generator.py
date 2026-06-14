from __future__ import annotations

from typing import Any

from quickapi.schema.validator import TYPE_NAMES


def schema_from_example(example: dict) -> dict:
    return {key: type(value).__name__ for key, value in (example or {}).items()}


def to_openapi_schema(schema: Any) -> dict[str, Any]:
    if not schema:
        return {"type": "object"}
    if isinstance(schema, type):
        return {"type": TYPE_NAMES.get(schema, "object")}
    if isinstance(schema, list):
        item = schema[0] if schema else str
        return {"type": "array", "items": to_openapi_schema(item)}
    if not isinstance(schema, dict):
        return {"type": "object"}

    if "type" in schema or "properties" in schema:
        result = dict(schema)
        if "properties" in result:
            result["properties"] = {
                key: to_openapi_schema(rule) for key, rule in (result.get("properties") or {}).items()
            }
        if "items" in result:
            result["items"] = to_openapi_schema(result["items"])
        result.pop("required", None) if isinstance(result.get("required"), bool) else None
        return result

    required = []
    properties = {}
    for field, rule in schema.items():
        field_schema, is_required = _field_to_openapi(rule)
        if is_required:
            required.append(field)
        properties[field] = field_schema
    result = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def _field_to_openapi(rule: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(rule, tuple) and rule:
        return to_openapi_schema(rule[0]), False
    if isinstance(rule, dict):
        required = bool(rule.get("required", True))
        schema = to_openapi_schema(rule)
        schema.pop("required", None)
        return schema, required
    return to_openapi_schema(rule), True
