from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any


@dataclass
class StandardSchema:
    name: str
    version: str
    schema: dict[str, Any]
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def clone(self) -> dict[str, Any]:
        return deepcopy(self.schema)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": list(self.tags),
        }


class SchemaRegistry:
    def __init__(self):
        self._schemas: dict[str, StandardSchema] = {}

    def register(self, name: str, schema: dict[str, Any], *, version: str = "1.0.0", description: str = "", tags: list[str] | None = None):
        self._schemas[name] = StandardSchema(name, version, deepcopy(schema), description, tags or [])
        return self

    def resolve(self, schema: Any) -> Any:
        if isinstance(schema, str):
            found = self._schemas.get(schema)
            return found.clone() if found else schema
        if isinstance(schema, dict) and "$standard" in schema:
            found = self._schemas.get(str(schema["$standard"]))
            if not found:
                return schema
            resolved = found.clone()
            overrides = {key: value for key, value in schema.items() if key != "$standard"}
            resolved.update(overrides)
            return resolved
        return schema

    def list(self) -> list[dict[str, Any]]:
        return [item.describe() for item in sorted(self._schemas.values(), key=lambda item: item.name)]


def create_default_schema_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    registry.register(
        "openrtb.bid_request",
        openrtb_bid_request_schema(),
        version="2.6-lite",
        description="Strict modular OpenRTB BidRequest guard schema subset for edge validation.",
        tags=["ads", "openrtb", "exchange", "strict-json"],
    )
    registry.register(
        "openrtb.imp",
        openrtb_imp_schema(),
        version="2.6-lite",
        description="OpenRTB impression object schema subset.",
        tags=["ads", "openrtb"],
    )
    return registry


def openrtb_bid_request_schema() -> dict[str, Any]:
    imp = openrtb_imp_schema()
    imp_defs = deepcopy(imp.get("$defs", {}))
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "quickapi:standards:openrtb:bid_request:2.6-lite",
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "imp"],
        "properties": {
            "id": {"type": "string", "minLength": 1, "maxLength": 128},
            "test": {"type": "integer", "enum": [0, 1]},
            "at": {"type": "integer", "enum": [1, 2, 3]},
            "tmax": {"type": "integer", "minimum": 1, "maximum": 10000},
            "cur": {"type": "array", "items": {"type": "string", "pattern": "^[A-Z]{3}$"}, "minItems": 1, "maxItems": 16, "uniqueItems": True},
            "bcat": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 64}, "maxItems": 256, "uniqueItems": True},
            "badv": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 256}, "maxItems": 1024, "uniqueItems": True},
            "imp": {"type": "array", "items": {"$ref": "#/$defs/Imp"}, "minItems": 1, "maxItems": 128},
            "site": {"$ref": "#/$defs/Site"},
            "app": {"$ref": "#/$defs/App"},
            "device": {"$ref": "#/$defs/Device"},
            "user": {"$ref": "#/$defs/User"},
            "regs": {"$ref": "#/$defs/Regs"},
            "source": {"$ref": "#/$defs/Source"},
            "ext": {"type": "object", "maxProperties": 250, "additionalProperties": True},
        },
        "anyOf": [{"required": ["site"]}, {"required": ["app"]}, {"required": ["device"]}],
        "$defs": {
            **imp_defs,
            "Imp": imp,
            "Metric": {
                "type": "object",
                "required": ["type", "value", "vendor"],
                "properties": {
                    "type": {"type": "string", "minLength": 1, "maxLength": 64},
                    "value": {"type": "number", "minimum": 0},
                    "vendor": {"type": "string", "minLength": 1, "maxLength": 128},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Site": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "maxLength": 128},
                    "name": {"type": "string", "maxLength": 256},
                    "domain": {"type": "string", "maxLength": 256},
                    "page": {"type": "string", "format": "url", "maxLength": 2048},
                    "cat": {"type": "array", "items": {"type": "string", "maxLength": 64}, "maxItems": 64},
                    "publisher": {"$ref": "#/$defs/Publisher"},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "App": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "maxLength": 128},
                    "name": {"type": "string", "maxLength": 256},
                    "bundle": {"type": "string", "maxLength": 512},
                    "domain": {"type": "string", "maxLength": 256},
                    "storeurl": {"type": "string", "format": "url", "maxLength": 2048},
                    "cat": {"type": "array", "items": {"type": "string", "maxLength": 64}, "maxItems": 64},
                    "publisher": {"$ref": "#/$defs/Publisher"},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Publisher": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "maxLength": 128},
                    "name": {"type": "string", "maxLength": 256},
                    "domain": {"type": "string", "maxLength": 256},
                    "cat": {"type": "array", "items": {"type": "string", "maxLength": 64}, "maxItems": 64},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Device": {
                "type": "object",
                "properties": {
                    "ua": {"type": "string", "maxLength": 2048},
                    "ip": {"type": "string", "format": "ipv4"},
                    "ipv6": {"type": "string", "maxLength": 64},
                    "devicetype": {"type": "integer", "minimum": 0, "maximum": 10},
                    "make": {"type": "string", "maxLength": 128},
                    "model": {"type": "string", "maxLength": 128},
                    "os": {"type": "string", "maxLength": 64},
                    "osv": {"type": "string", "maxLength": 64},
                    "h": {"type": "integer", "minimum": 0, "maximum": 20000},
                    "w": {"type": "integer", "minimum": 0, "maximum": 20000},
                    "ifa": {"type": "string", "maxLength": 128},
                    "lmt": {"type": "integer", "enum": [0, 1]},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "maxLength": 256},
                    "buyeruid": {"type": "string", "maxLength": 256},
                    "yob": {"type": "integer", "minimum": 1900, "maximum": 2100},
                    "gender": {"type": "string", "enum": ["M", "F", "O"]},
                    "keywords": {"type": "string", "maxLength": 2048},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Regs": {
                "type": "object",
                "properties": {
                    "coppa": {"type": "integer", "enum": [0, 1]},
                    "gdpr": {"type": "integer", "enum": [0, 1]},
                    "us_privacy": {"type": "string", "maxLength": 16},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Source": {
                "type": "object",
                "properties": {
                    "fd": {"type": "integer", "enum": [0, 1]},
                    "tid": {"type": "string", "maxLength": 128},
                    "pchain": {"type": "string", "maxLength": 4096},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
        },
    }


def openrtb_imp_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "minLength": 1, "maxLength": 128},
            "metric": {"type": "array", "items": {"$ref": "#/$defs/Metric"}, "maxItems": 32},
            "banner": {"$ref": "#/$defs/Banner"},
            "video": {"$ref": "#/$defs/Video"},
            "audio": {"$ref": "#/$defs/Audio"},
            "native": {"$ref": "#/$defs/Native"},
            "pmp": {"$ref": "#/$defs/Pmp"},
            "displaymanager": {"type": "string", "maxLength": 128},
            "tagid": {"type": "string", "maxLength": 256},
            "bidfloor": {"type": "number", "minimum": 0},
            "bidfloorcur": {"type": "string", "pattern": "^[A-Z]{3}$"},
            "secure": {"type": "integer", "enum": [0, 1]},
            "exp": {"type": "integer", "minimum": 0, "maximum": 86400},
            "ext": {"type": "object", "additionalProperties": True},
        },
        "anyOf": [{"required": ["banner"]}, {"required": ["video"]}, {"required": ["audio"]}, {"required": ["native"]}],
        "$defs": {
            "Metric": {
                "type": "object",
                "required": ["type", "value", "vendor"],
                "properties": {
                    "type": {"type": "string", "minLength": 1, "maxLength": 64},
                    "value": {"type": "number", "minimum": 0},
                    "vendor": {"type": "string", "minLength": 1, "maxLength": 128},
                },
            },
            "Banner": {
                "type": "object",
                "properties": {
                    "w": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "h": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "format": {"type": "array", "items": {"$ref": "#/$defs/Format"}, "maxItems": 32},
                    "btype": {"type": "array", "items": {"type": "integer"}, "maxItems": 32, "uniqueItems": True},
                    "battr": {"type": "array", "items": {"type": "integer"}, "maxItems": 128, "uniqueItems": True},
                    "pos": {"type": "integer", "minimum": 0, "maximum": 7},
                    "mimes": {"type": "array", "items": {"type": "string", "maxLength": 128}, "maxItems": 64},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Format": {
                "type": "object",
                "properties": {
                    "w": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "h": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "wratio": {"type": "integer", "minimum": 1, "maximum": 10000},
                    "hratio": {"type": "integer", "minimum": 1, "maximum": 10000},
                    "wmin": {"type": "integer", "minimum": 1, "maximum": 20000},
                },
            },
            "Video": {
                "type": "object",
                "required": ["mimes"],
                "properties": {
                    "mimes": {"type": "array", "items": {"type": "string", "maxLength": 128}, "minItems": 1, "maxItems": 64},
                    "minduration": {"type": "integer", "minimum": 0, "maximum": 86400},
                    "maxduration": {"type": "integer", "minimum": 0, "maximum": 86400},
                    "protocols": {"type": "array", "items": {"type": "integer"}, "maxItems": 32, "uniqueItems": True},
                    "w": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "h": {"type": "integer", "minimum": 1, "maximum": 20000},
                    "startdelay": {"type": "integer", "minimum": -2, "maximum": 86400},
                    "placement": {"type": "integer", "minimum": 0, "maximum": 10},
                    "linearity": {"type": "integer", "enum": [1, 2]},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Audio": {
                "type": "object",
                "required": ["mimes"],
                "properties": {
                    "mimes": {"type": "array", "items": {"type": "string", "maxLength": 128}, "minItems": 1, "maxItems": 64},
                    "minduration": {"type": "integer", "minimum": 0, "maximum": 86400},
                    "maxduration": {"type": "integer", "minimum": 0, "maximum": 86400},
                    "protocols": {"type": "array", "items": {"type": "integer"}, "maxItems": 32, "uniqueItems": True},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Native": {
                "type": "object",
                "required": ["request"],
                "properties": {
                    "request": {"type": "string", "minLength": 2, "maxLength": 100000},
                    "ver": {"type": "string", "maxLength": 16},
                    "api": {"type": "array", "items": {"type": "integer"}, "maxItems": 32, "uniqueItems": True},
                    "battr": {"type": "array", "items": {"type": "integer"}, "maxItems": 128, "uniqueItems": True},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Pmp": {
                "type": "object",
                "properties": {
                    "private_auction": {"type": "integer", "enum": [0, 1]},
                    "deals": {"type": "array", "items": {"$ref": "#/$defs/Deal"}, "maxItems": 256},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
            "Deal": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string", "minLength": 1, "maxLength": 128},
                    "bidfloor": {"type": "number", "minimum": 0},
                    "bidfloorcur": {"type": "string", "pattern": "^[A-Z]{3}$"},
                    "at": {"type": "integer", "enum": [1, 2, 3]},
                    "wseat": {"type": "array", "items": {"type": "string", "maxLength": 128}, "maxItems": 256},
                    "wadomain": {"type": "array", "items": {"type": "string", "maxLength": 256}, "maxItems": 256},
                    "ext": {"type": "object", "additionalProperties": True},
                },
            },
        },
    }
