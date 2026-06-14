from __future__ import annotations

from dataclasses import dataclass
import re
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
    "null": lambda value: value is None,
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
    code: str = "VALIDATION_ERROR"
    severity: str = "error"
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "where": self.where,
            "message": self.message,
            "code": self.code,
            "severity": self.severity,
        }
        if self.expected is not None:
            payload["expected"] = self.expected
        if self.received is not None:
            payload["received"] = self.received
        if self.hint is not None:
            payload["hint"] = self.hint
        return payload


def require_fields(body: dict, fields: list[str]) -> list[str]:
    body = body or {}
    return [field for field in fields if field not in body]


def validate_payload(value: Any, schema: Any, *, location: str = "body") -> list[dict[str, Any]]:
    if not schema:
        return []
    normalized = _normalize_schema(schema)
    issues = _validate(value, normalized, location, root=normalized, seen_refs=set())
    return [issue.to_dict() for issue in issues]


def validate_runtime_shape(
    value: Any,
    *,
    location: str = "body",
    max_depth: int = 12,
    max_string_length: int = 4096,
    max_array_length: int = 1000,
    max_object_keys: int = 250,
) -> list[dict[str, Any]]:
    issues = _validate_shape(
        value,
        location=location,
        depth=0,
        max_depth=max_depth,
        max_string_length=max_string_length,
        max_array_length=max_array_length,
        max_object_keys=max_object_keys,
    )
    return [issue.to_dict() for issue in issues]


def _validate(
    value: Any,
    schema: dict[str, Any],
    location: str,
    *,
    root: dict[str, Any],
    seen_refs: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(schema, dict):
        return issues

    if "$ref" in schema:
        ref = str(schema["$ref"])
        if ref in seen_refs:
            return [
                ValidationIssue(
                    where=location,
                    message="Schema reference cycle detected",
                    expected=ref,
                    code="SCHEMA_REF_CYCLE",
                    hint="Break the recursive $ref or validate this model in application code.",
                )
            ]
        resolved = _resolve_ref(ref, root)
        if resolved is None:
            return [
                ValidationIssue(
                    where=location,
                    message="Schema reference could not be resolved",
                    expected=ref,
                    code="SCHEMA_REF_NOT_FOUND",
                    hint="Use local JSON pointers such as #/$defs/Imp or #/definitions/Imp.",
                )
            ]
        merged = dict(resolved)
        for key, item in schema.items():
            if key != "$ref":
                merged[key] = item
        return _validate(value, _normalize_schema(merged), location, root=root, seen_refs=seen_refs | {ref})

    issues.extend(_validate_composition(value, schema, location, root=root, seen_refs=seen_refs))
    if issues and schema.get("x-stop-on-composition-error"):
        return issues

    if schema.get("nullable") is True and value is None:
        return issues

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        expected_type = "|".join(str(item) for item in expected_type)
    if expected_type and not _matches_type(value, str(expected_type)):
        return [
            *issues,
            ValidationIssue(
                where=location,
                message=f"{location} must be {expected_type}",
                expected=str(expected_type),
                received=_received_type(value),
                code="TYPE",
                hint="Send JSON data with the type declared by the route schema.",
            ),
        ]

    if value is None:
        issues.extend(_validate_scalar_rules(value, schema, location))
        return issues

    object_keywords = {
        "properties",
        "patternProperties",
        "pattern_properties",
        "required",
        "additionalProperties",
        "additional_properties",
        "unevaluatedProperties",
        "unevaluated_properties",
        "minProperties",
        "maxProperties",
        "min_properties",
        "max_properties",
        "dependentRequired",
        "dependent_required",
        "dependencies",
        "propertyNames",
        "property_names",
    }
    if (expected_type == "object" or any(key in schema for key in object_keywords)) and isinstance(value, dict):
        issues.extend(_validate_object(value, schema, location, root=root, seen_refs=seen_refs))

    if (expected_type == "array" or "items" in schema or "prefixItems" in schema) and isinstance(value, list):
        issues.extend(_validate_array(value, schema, location, root=root, seen_refs=seen_refs))

    issues.extend(_validate_scalar_rules(value, schema, location))
    return issues


def _validate_composition(
    value: Any,
    schema: dict[str, Any],
    location: str,
    *,
    root: dict[str, Any],
    seen_refs: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    all_of = schema.get("allOf") or schema.get("all_of")
    if all_of:
        for index, part in enumerate(all_of):
            part_issues = _validate(value, _normalize_schema(part), location, root=root, seen_refs=set(seen_refs))
            issues.extend(
                _with_prefix(part_issues, f"allOf[{index}]", "ALLOF", "Value failed an allOf schema branch.")
            )

    any_of = schema.get("anyOf") or schema.get("any_of")
    if any_of:
        branch_results = [
            _validate(value, _normalize_schema(part), location, root=root, seen_refs=set(seen_refs))
            for part in any_of
        ]
        if not any(not result for result in branch_results):
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} must match at least one anyOf schema",
                    expected="anyOf",
                    received=_received_type(value),
                    code="ANYOF",
                    hint=_composition_hint(branch_results),
                )
            )

    one_of = schema.get("oneOf") or schema.get("one_of")
    if one_of:
        branch_results = [
            _validate(value, _normalize_schema(part), location, root=root, seen_refs=set(seen_refs))
            for part in one_of
        ]
        matched = [index for index, result in enumerate(branch_results) if not result]
        if len(matched) != 1:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} must match exactly one oneOf schema",
                    expected="oneOf",
                    received=f"{len(matched)} matches",
                    code="ONEOF",
                    hint="Use a discriminator field or make the branches mutually exclusive.",
                )
            )

    not_schema = schema.get("not")
    if not_schema:
        not_issues = _validate(value, _normalize_schema(not_schema), location, root=root, seen_refs=set(seen_refs))
        if not not_issues:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} matches a forbidden schema",
                    expected="not",
                    received=_received_type(value),
                    code="NOT",
                )
            )
    return issues


def _validate_object(
    value: dict[str, Any],
    schema: dict[str, Any],
    location: str,
    *,
    root: dict[str, Any],
    seen_refs: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    required = set(schema.get("required") or [])
    properties = schema.get("properties") or {}
    pattern_properties = schema.get("patternProperties") or schema.get("pattern_properties") or {}

    if "minProperties" in schema or "min_properties" in schema:
        minimum = int(schema.get("minProperties", schema.get("min_properties")))
        if len(value) < minimum:
            issues.append(_issue(location, "MIN_PROPERTIES", f"{location} has too few properties", f"minProperties={minimum}", str(len(value))))
    if "maxProperties" in schema or "max_properties" in schema:
        maximum = int(schema.get("maxProperties", schema.get("max_properties")))
        if len(value) > maximum:
            issues.append(_issue(location, "MAX_PROPERTIES", f"{location} has too many properties", f"maxProperties={maximum}", str(len(value))))

    for field in sorted(required):
        if field not in value or value[field] is None:
            issues.append(
                ValidationIssue(
                    where=f"{location}.{field}",
                    message=f"{field} is required",
                    expected="required",
                    received="missing",
                    code="REQUIRED_FIELD_MISSING",
                    hint=f"Add '{field}' to {location}.",
                )
            )

    property_names = schema.get("propertyNames") or schema.get("property_names")
    if property_names:
        for field in value:
            issues.extend(
                _validate(field, _normalize_schema(property_names), f"{location}.{field}#name", root=root, seen_refs=set(seen_refs))
            )

    dependent_required = schema.get("dependentRequired") or schema.get("dependent_required") or schema.get("dependencies") or {}
    for source, required_fields in dependent_required.items():
        if source not in value or not isinstance(required_fields, list | tuple | set):
            continue
        for field in required_fields:
            if field not in value:
                issues.append(
                    ValidationIssue(
                        where=f"{location}.{field}",
                        message=f"{field} is required when {source} is present",
                        expected=f"dependentRequired:{source}",
                        received="missing",
                        code="DEPENDENT_REQUIRED",
                    )
                )

    matched_fields: set[str] = set()
    for field, rule in properties.items():
        if field not in value or value[field] is None:
            continue
        matched_fields.add(field)
        issues.extend(_validate(value[field], _normalize_schema(rule), f"{location}.{field}", root=root, seen_refs=set(seen_refs)))

    for pattern, rule in pattern_properties.items():
        compiled = re.compile(str(pattern))
        for field, item in value.items():
            if compiled.search(str(field)):
                matched_fields.add(field)
                issues.extend(_validate(item, _normalize_schema(rule), f"{location}.{field}", root=root, seen_refs=set(seen_refs)))

    additional = schema.get("additionalProperties", schema.get("additional_properties", True))
    unevaluated = schema.get("unevaluatedProperties", schema.get("unevaluated_properties", None))
    extra_fields = sorted(set(value) - matched_fields)
    additional_rule = unevaluated if unevaluated is not None else additional
    if additional_rule is False:
        for field in extra_fields:
            issues.append(
                ValidationIssue(
                    where=f"{location}.{field}",
                    message=f"{field} is not allowed",
                    expected="known property",
                    received="extra property",
                    code="UNKNOWN_FIELD",
                    hint="Remove this field or declare it in properties/patternProperties.",
                )
            )
    elif isinstance(additional_rule, dict):
        for field in extra_fields:
            issues.extend(
                _validate(value[field], _normalize_schema(additional_rule), f"{location}.{field}", root=root, seen_refs=set(seen_refs))
            )

    return issues


def _validate_array(
    value: list[Any],
    schema: dict[str, Any],
    location: str,
    *,
    root: dict[str, Any],
    seen_refs: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    prefix_items = schema.get("prefixItems") or schema.get("prefix_items")
    if prefix_items:
        for index, rule in enumerate(prefix_items):
            if index >= len(value):
                break
            issues.extend(_validate(value[index], _normalize_schema(rule), f"{location}[{index}]", root=root, seen_refs=set(seen_refs)))
        if schema.get("items") is False and len(value) > len(prefix_items):
            for index in range(len(prefix_items), len(value)):
                issues.append(
                    ValidationIssue(
                        where=f"{location}[{index}]",
                        message=f"{location}[{index}] is not allowed",
                        expected="tuple length",
                        received=_received_type(value[index]),
                        code="ADDITIONAL_ITEM",
                    )
                )
    elif "items" in schema and schema["items"] is not False:
        item_schema = _normalize_schema(schema["items"])
        for index, item in enumerate(value):
            issues.extend(_validate(item, item_schema, f"{location}[{index}]", root=root, seen_refs=set(seen_refs)))

    if schema.get("uniqueItems") or schema.get("unique_items"):
        seen: set[str] = set()
        for index, item in enumerate(value):
            marker = repr(_stable_marker(item))
            if marker in seen:
                issues.append(
                    ValidationIssue(
                        where=f"{location}[{index}]",
                        message=f"{location} must contain unique items",
                        expected="uniqueItems=true",
                        received=repr(item)[:120],
                        code="UNIQUE_ITEMS",
                    )
                )
            seen.add(marker)

    contains = schema.get("contains")
    if contains:
        results = [
            _validate(item, _normalize_schema(contains), f"{location}[{index}]", root=root, seen_refs=set(seen_refs))
            for index, item in enumerate(value)
        ]
        matches = sum(1 for result in results if not result)
        minimum = int(schema.get("minContains", schema.get("min_contains", 1)))
        maximum = schema.get("maxContains", schema.get("max_contains"))
        if matches < minimum:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} does not contain enough matching items",
                    expected=f"minContains={minimum}",
                    received=str(matches),
                    code="MIN_CONTAINS",
                )
            )
        if maximum is not None and matches > int(maximum):
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} contains too many matching items",
                    expected=f"maxContains={maximum}",
                    received=str(matches),
                    code="MAX_CONTAINS",
                )
            )

    return issues


def _validate_scalar_rules(value: Any, schema: dict[str, Any], location: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if value is None:
        return issues

    min_length = schema.get("minLength", schema.get("min_length"))
    max_length = schema.get("maxLength", schema.get("max_length"))
    if min_length is not None and hasattr(value, "__len__") and len(value) < int(min_length):
        issues.append(_issue(location, "MIN_LENGTH", f"{location} is shorter than minLength", f"minLength={min_length}", str(len(value))))
    if max_length is not None and hasattr(value, "__len__") and len(value) > int(max_length):
        issues.append(_issue(location, "MAX_LENGTH", f"{location} is longer than maxLength", f"maxLength={max_length}", str(len(value))))

    min_items = schema.get("minItems", schema.get("min_items"))
    max_items = schema.get("maxItems", schema.get("max_items"))
    if min_items is not None and isinstance(value, list) and len(value) < int(min_items):
        issues.append(_issue(location, "MIN_ITEMS", f"{location} has fewer items than minItems", f"minItems={min_items}", str(len(value))))
    if max_items is not None and isinstance(value, list) and len(value) > int(max_items):
        issues.append(_issue(location, "MAX_ITEMS", f"{location} has more items than maxItems", f"maxItems={max_items}", str(len(value))))

    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    exclusive_minimum = schema.get("exclusiveMinimum", schema.get("exclusive_minimum"))
    exclusive_maximum = schema.get("exclusiveMaximum", schema.get("exclusive_maximum"))
    if minimum is not None and isinstance(value, int | float) and value < float(minimum):
        issues.append(_issue(location, "MINIMUM", f"{location} is below minimum", f"minimum={minimum}", str(value)))
    if maximum is not None and isinstance(value, int | float) and value > float(maximum):
        issues.append(_issue(location, "MAXIMUM", f"{location} is above maximum", f"maximum={maximum}", str(value)))
    if exclusive_minimum is not None and isinstance(value, int | float) and value <= float(exclusive_minimum):
        issues.append(_issue(location, "EXCLUSIVE_MINIMUM", f"{location} must be greater than exclusiveMinimum", f"exclusiveMinimum={exclusive_minimum}", str(value)))
    if exclusive_maximum is not None and isinstance(value, int | float) and value >= float(exclusive_maximum):
        issues.append(_issue(location, "EXCLUSIVE_MAXIMUM", f"{location} must be less than exclusiveMaximum", f"exclusiveMaximum={exclusive_maximum}", str(value)))

    multiple_of = schema.get("multipleOf", schema.get("multiple_of"))
    if multiple_of is not None and isinstance(value, int | float):
        divisor = float(multiple_of)
        if divisor and value % divisor != 0:
            issues.append(_issue(location, "MULTIPLE_OF", f"{location} must be a multiple of {multiple_of}", f"multipleOf={multiple_of}", str(value)))

    if "enum" in schema and value not in schema["enum"]:
        issues.append(_issue(location, "ENUM", f"{location} must be one of the allowed values", f"enum={schema['enum']}", repr(value)))
    if "const" in schema and value != schema["const"]:
        issues.append(_issue(location, "CONST", f"{location} must match the constant value", repr(schema["const"]), repr(value)))

    if "pattern" in schema and isinstance(value, str) and re.search(str(schema["pattern"]), value) is None:
        issues.append(_issue(location, "PATTERN", f"{location} does not match required pattern", f"pattern={schema['pattern']}", value[:120]))
    if "format" in schema and isinstance(value, str):
        issue = _validate_format(value, str(schema["format"]), location)
        if issue:
            issues.append(issue)
    return issues


def _normalize_schema(schema: Any) -> dict[str, Any]:
    if isinstance(schema, type):
        return {"type": TYPE_NAMES.get(schema, "object")}
    if isinstance(schema, list):
        item = schema[0] if schema else Any
        return {"type": "array", "items": _normalize_schema(item)}
    if not isinstance(schema, dict):
        return {"type": "object"}

    schema_keys = {
        "$schema", "$id", "$defs", "definitions", "$ref", "type", "properties", "patternProperties",
        "additionalProperties", "unevaluatedProperties", "items", "prefixItems", "required",
        "oneOf", "anyOf", "allOf", "not", "enum", "const", "format", "pattern", "minimum", "maximum",
        "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems",
        "maxItems", "minProperties", "maxProperties", "dependentRequired", "dependencies", "contains",
        "minContains", "maxContains", "nullable", "uniqueItems", "propertyNames",
        "additional_properties", "pattern_properties", "one_of", "any_of", "all_of", "min_length",
        "max_length", "min_items", "max_items", "min_properties", "max_properties", "dependent_required",
        "prefix_items", "unique_items", "property_names",
    }
    if any(key in schema for key in schema_keys):
        normalized = dict(schema)
        if "properties" in normalized:
            normalized["properties"] = {
                key: _normalize_schema(rule) for key, rule in (normalized.get("properties") or {}).items()
            }
        for key in ("patternProperties", "pattern_properties"):
            if key in normalized:
                normalized[key] = {pattern: _normalize_schema(rule) for pattern, rule in (normalized.get(key) or {}).items()}
        for key in ("items", "contains", "not", "propertyNames", "property_names", "additionalProperties", "additional_properties", "unevaluatedProperties", "unevaluated_properties"):
            if isinstance(normalized.get(key), dict):
                normalized[key] = _normalize_schema(normalized[key])
        for key in ("prefixItems", "prefix_items", "oneOf", "one_of", "anyOf", "any_of", "allOf", "all_of"):
            if isinstance(normalized.get(key), list):
                normalized[key] = [_normalize_schema(item) for item in normalized[key]]
        for defs_key in ("$defs", "definitions"):
            if isinstance(normalized.get(defs_key), dict):
                normalized[defs_key] = {name: _normalize_schema(rule) for name, rule in normalized[defs_key].items()}
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
    if "|" in expected_type:
        return any(_matches_type(value, item.strip()) for item in expected_type.split("|"))
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


def _validate_shape(
    value: Any,
    *,
    location: str,
    depth: int,
    max_depth: int,
    max_string_length: int,
    max_array_length: int,
    max_object_keys: int,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if depth > max_depth:
        return [
            ValidationIssue(
                where=location,
                message=f"{location} is nested too deeply",
                expected=f"max_depth={max_depth}",
                received=str(depth),
                code="MAX_DEPTH",
                hint="Flatten the JSON payload or raise the configured guard limit.",
            )
        ]
    if isinstance(value, str):
        if len(value) > max_string_length:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} string is too long",
                    expected=f"max_string_length={max_string_length}",
                    received=str(len(value)),
                    code="STRING_TOO_LONG",
                    hint="Send a shorter string or configure ml_guard_max_string_length.",
                )
            )
        return issues
    if isinstance(value, list):
        if len(value) > max_array_length:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} array has too many items",
                    expected=f"max_array_length={max_array_length}",
                    received=str(len(value)),
                    code="ARRAY_TOO_LONG",
                    hint="Page the data or configure ml_guard_max_array_length.",
                )
            )
        for index, item in enumerate(value[: max_array_length + 1]):
            issues.extend(
                _validate_shape(
                    item,
                    location=f"{location}[{index}]",
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_string_length=max_string_length,
                    max_array_length=max_array_length,
                    max_object_keys=max_object_keys,
                )
            )
        return issues
    if isinstance(value, dict):
        if len(value) > max_object_keys:
            issues.append(
                ValidationIssue(
                    where=location,
                    message=f"{location} object has too many keys",
                    expected=f"max_object_keys={max_object_keys}",
                    received=str(len(value)),
                    code="OBJECT_TOO_WIDE",
                    hint="Split the payload or configure ml_guard_max_object_keys.",
                )
            )
        for key, item in list(value.items())[: max_object_keys + 1]:
            if not isinstance(key, str):
                issues.append(_issue(location, "INVALID_KEY_TYPE", "JSON object keys must be strings", "string key", type(key).__name__))
                continue
            if any(ord(ch) < 32 for ch in key):
                issues.append(_issue(f"{location}.{key!r}", "CONTROL_CHARACTER", "JSON object key contains control characters", "printable key", repr(key)))
            issues.extend(
                _validate_shape(
                    item,
                    location=f"{location}.{key}",
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_string_length=max_string_length,
                    max_array_length=max_array_length,
                    max_object_keys=max_object_keys,
                )
            )
    return issues


def _resolve_ref(ref: str, root: dict[str, Any]) -> dict[str, Any] | None:
    if not ref.startswith("#"):
        return None
    if ref == "#":
        return root
    pointer = ref[1:]
    if not pointer.startswith("/"):
        return None
    current: Any = root
    for part in pointer.strip("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current if isinstance(current, dict) else None


def _validate_format(value: str, format_name: str, location: str) -> ValidationIssue | None:
    patterns = {
        "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
        "slug": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        "url": r"^https?://[^\s/$.?#].[^\s]*$",
        "uri": r"^[a-zA-Z][a-zA-Z0-9+.-]*:[^\s]*$",
        "ipv4": r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$",
        "date": r"^\d{4}-\d{2}-\d{2}$",
        "time": r"^\d{2}:\d{2}:\d{2}",
        "datetime": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        "date-time": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        "phone": r"^\+?[0-9][0-9\s().-]{6,24}$",
    }
    pattern = patterns.get(format_name)
    if pattern is None:
        return None
    if re.search(pattern, value):
        return None
    return ValidationIssue(
        where=location,
        message=f"{location} is not a valid {format_name}",
        expected=f"format={format_name}",
        received=value[:120],
        code="FORMAT",
        hint=f"Send a value matching the {format_name} format.",
    )


def _issue(location: str, code: str, message: str, expected: str | None = None, received: str | None = None) -> ValidationIssue:
    return ValidationIssue(where=location, message=message, expected=expected, received=received, code=code)


def _with_prefix(issues: list[ValidationIssue], prefix: str, code: str, default_message: str) -> list[ValidationIssue]:
    if not issues:
        return []
    return [
        ValidationIssue(
            where=issue.where,
            message=f"{prefix}: {issue.message or default_message}",
            expected=issue.expected,
            received=issue.received,
            code=code,
            hint=issue.hint,
        )
        for issue in issues
    ]


def _composition_hint(branch_results: list[list[ValidationIssue]]) -> str:
    first_issue = next((result[0] for result in branch_results if result), None)
    if first_issue is None:
        return "No anyOf branch matched."
    return f"Closest branch failed at {first_issue.where}: {first_issue.message}"


def _stable_marker(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _stable_marker(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_stable_marker(item) for item in value)
    return value
