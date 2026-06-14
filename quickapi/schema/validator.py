from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TYPE_NAMES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
}

JSON_TYPE_CHECKS = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: (isinstance(value, int | float) and not isinstance(value, bool)),
    "boolean": lambda value: isinstance(value, bool),
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
}


@dataclass
class ValidationIssue:
    where: str
    message: str
    expected: str | None = None
    received: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {"where": self.where, "message": self.message}
        if self.expected is not None:
            payload["expected"] = self.expected
        if self.received is not None:
            payload["received"] = self.received
        return payload


def require_fields(body: dict, fields: list[str]) -> list[str]:
    body = body or {}
    return [field for field in fields if field not in body]


def validate_payload(value: Any, schema: Any, *, location: str = "body") -> list[dict[str, Any]]:
    if not schema:
        return []
    issues = _validate(value, _normalize_schema(schema), location)
    return [issue.to_dict() for issue in issues]


def _validate(value: Any, schema: dict[str, Any], location: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        return [
            ValidationIssue(
                where=location,
                message=f"{location} must be {expected_type}",
                expected=expected_type,
                received=_received_type(value),
            )
        ]

    if expected_type == "object" or "properties" in schema:
        if value is None:
            value = {}
        if not isinstance(value, dict):
            return [
                ValidationIssue(
                    where=location,
                    message=f"{location} must be an object",
                    expected="object",
                    received=_received_type(value),
                )
            ]
        required = set(schema.get("required") or [])
        properties = schema.get("properties") or {}
        for field in sorted(required):
            if field not in value or value[field] is None:
                issues.append(
                    ValidationIssue(
                        where=f"{location}.{field}",
                        message=f"{field} is required",
                        expected="required",
                        received="missing",
                    )
                )
        for field, rule in properties.items():
            if field not in value or value[field] is None:
                continue
            issues.extend(_validate(value[field], _normalize_schema(rule), f"{location}.{field}"))

    if expected_type == "array" and "items" in schema and isinstance(value, list):
        item_schema = _normalize_schema(schema["items"])
        for index, item in enumerate(value):
            issues.extend(_validate(item, item_schema, f"{location}[{index}]"))

    issues.extend(_validate_scalar_rules(value, schema, location))
    return issues


def _validate_scalar_rules(value: Any, schema: dict[str, Any], location: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if value is None:
        return issues

    if "min_length" in schema and hasattr(value, "__len__") and len(value) < int(schema["min_length"]):
        issues.append(
            ValidationIssue(
                where=location,
                message=f"{location} is shorter than min_length",
                expected=f"min_length={schema['min_length']}",
                received=str(len(value)),
            )
        )
    if "max_length" in schema and hasattr(value, "__len__") and len(value) > int(schema["max_length"]):
        issues.append(
            ValidationIssue(
                where=location,
                message=f"{location} is longer than max_length",
                expected=f"max_length={schema['max_length']}",
                received=str(len(value)),
            )
        )
    if "minimum" in schema and isinstance(value, int | float) and value < float(schema["minimum"]):
        issues.append(
            ValidationIssue(
                where=location,
                message=f"{location} is below minimum",
                expected=f"minimum={schema['minimum']}",
                received=str(value),
            )
        )
    if "maximum" in schema and isinstance(value, int | float) and value > float(schema["maximum"]):
        issues.append(
            ValidationIssue(
                where=location,
                message=f"{location} is above maximum",
                expected=f"maximum={schema['maximum']}",
                received=str(value),
            )
        )
    if "enum" in schema and value not in schema["enum"]:
        issues.append(
            ValidationIssue(
                where=location,
                message=f"{location} must be one of the allowed values",
                expected=f"enum={schema['enum']}",
                received=repr(value),
            )
        )
    return issues


def _normalize_schema(schema: Any) -> dict[str, Any]:
    if isinstance(schema, type):
        return {"type": TYPE_NAMES.get(schema, "object")}
    if isinstance(schema, list):
        item = schema[0] if schema else Any
        return {"type": "array", "items": _normalize_schema(item)}
    if not isinstance(schema, dict):
        return {"type": "object"}

    if "type" in schema or "properties" in schema:
        normalized = dict(schema)
        if "properties" in normalized:
            normalized["properties"] = {
                key: _normalize_schema(rule) for key, rule in (normalized.get("properties") or {}).items()
            }
        if "items" in normalized:
            normalized["items"] = _normalize_schema(normalized["items"])
        return normalized

    required = []
    properties = {}
    for field, rule in schema.items():
        field_rule = _normalize_field_rule(rule)
        if field_rule.pop("required", True):
            required.append(field)
        properties[field] = field_rule
    return {"type": "object", "required": required, "properties": properties}


def _normalize_field_rule(rule: Any) -> dict[str, Any]:
    if isinstance(rule, type):
        return {"type": TYPE_NAMES.get(rule, "object"), "required": True}
    if isinstance(rule, list):
        item = rule[0] if rule else Any
        return {"type": "array", "items": _normalize_schema(item), "required": True}
    if isinstance(rule, tuple) and rule:
        return {"type": TYPE_NAMES.get(rule[0], "object"), "required": False}
    if isinstance(rule, dict):
        normalized = _normalize_schema(rule)
        normalized.setdefault("required", rule.get("required", True))
        return normalized
    return {"type": "object", "required": True}


def _matches_type(value: Any, expected_type: str) -> bool:
    checker = JSON_TYPE_CHECKS.get(expected_type)
    if checker is None:
        return True
    return checker(value)


def _received_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__
