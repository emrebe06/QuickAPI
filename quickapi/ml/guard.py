from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import blake2b
from math import log10
from time import perf_counter
from typing import Any

from quickapi.ml.engine import MLEngine
from quickapi.ml.intent import infer_intent
from quickapi.ml.risk import extract_features, score_bot, score_risk
from quickapi.ml.synaptic import SynapticDecision, SynapticLayer


class GuardAction(StrEnum):
    ALLOW = "allow"
    OBSERVE = "observe"
    CHALLENGE = "challenge"
    BLOCK = "block"


class GuardSignalKind(StrEnum):
    DATA = "data"
    SECURITY = "security"
    BOT = "bot"
    ANOMALY = "anomaly"
    NATIVE = "native"
    POLICY = "policy"
    SYSTEM = "system"


@dataclass
class GuardSignal:
    code: str
    message: str
    kind: str = GuardSignalKind.SECURITY
    severity: str = "medium"
    score: float = 0.0
    where: str | None = None
    hint: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "code": self.code,
            "message": self.message,
            "kind": str(self.kind),
            "severity": self.severity,
            "score": round(float(self.score), 4),
        }
        if self.where:
            data["where"] = self.where
        if self.hint:
            data["hint"] = self.hint
        if self.evidence:
            data["evidence"] = dict(self.evidence)
        return data


@dataclass
class RequestProfile:
    method: str
    path: str
    intent: str
    route_name: str | None
    route_sensitivity: int
    body_bytes: int
    query_count: int
    header_count: int
    content_type: str
    user_agent: str
    fingerprint: str
    shape: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "intent": self.intent,
            "route_name": self.route_name,
            "route_sensitivity": self.route_sensitivity,
            "body_bytes": self.body_bytes,
            "query_count": self.query_count,
            "header_count": self.header_count,
            "content_type": self.content_type,
            "user_agent": self.user_agent[:160],
            "fingerprint": self.fingerprint,
            "shape": dict(self.shape),
        }


@dataclass
class GuardReport:
    enabled: bool
    action: str = GuardAction.ALLOW
    risk_score: float = 0.0
    confidence: float = 0.0
    duration_ms: float = 0.0
    profile: RequestProfile | None = None
    signals: list[GuardSignal] = field(default_factory=list)
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    synaptic: dict[str, Any] | None = None
    ml: dict[str, Any] | None = None
    native: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    last_error: dict[str, Any] | None = None

    @property
    def blocked(self) -> bool:
        return self.action == GuardAction.BLOCK

    def to_dict(self) -> dict[str, Any]:
        data = {
            "enabled": self.enabled,
            "action": str(self.action),
            "risk_score": round(float(self.risk_score), 4),
            "confidence": round(float(self.confidence), 4),
            "duration_ms": self.duration_ms,
            "signals": [signal.to_dict() for signal in self.signals],
            "validation_issues": list(self.validation_issues),
        }
        if self.profile is not None:
            data["profile"] = self.profile.to_dict()
        if self.synaptic is not None:
            data["synaptic"] = self.synaptic
        if self.ml is not None:
            data["ml"] = self.ml
        if self.native is not None:
            data["native"] = self.native
        if self.policy is not None:
            data["policy"] = self.policy
        if self.last_error is not None:
            data["last_error"] = self.last_error
        return data


@dataclass
class GuardConfig:
    enabled: bool = False
    block_enabled: bool = True
    strict_validation: bool = True
    max_body_size: int = 1024 * 1024
    max_string_length: int = 4096
    max_array_length: int = 1000
    max_object_keys: int = 250
    observe_threshold: float = 0.38
    challenge_threshold: float = 0.68
    block_threshold: float = 0.88


class MLGuard:
    """A worker-style guard that combines rules, validation, native policy and ML."""

    ADMIN_HINTS = ("/admin", "/internal", "/system", "/debug", "/ops")
    AUTH_HINTS = ("/auth", "/login", "/logout", "/token", "/session", "/users")
    PAYMENT_HINTS = ("/payment", "/checkout", "/orders", "/invoice", "/billing")
    TOOL_HINTS = ("/quick/tools", "/quick/plugins", "/quick/agents", "/quick/llm", "/quick/webhooks")
    FILE_HINTS = ("/upload", "/download", "/file", "/media", "/convert")

    HIGH_RISK_EXTENSIONS = (
        ".php",
        ".phtml",
        ".asp",
        ".aspx",
        ".jsp",
        ".exe",
        ".bat",
        ".cmd",
        ".ps1",
        ".sh",
        ".dll",
        ".so",
    )
    SECRET_TOKENS = (
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "access_token",
        "refresh_token",
        "private_key",
        "authorization",
    )
    SSRF_TOKENS = (
        "169.254.169.254",
        "metadata.google.internal",
        "localhost:",
        "127.0.0.1:",
        "0.0.0.0:",
        "file://",
        "gopher://",
        "ftp://",
    )
    CODE_TOKENS = (
        "eval(",
        "exec(",
        "subprocess",
        "os.system",
        "child_process",
        "require(",
        "importlib",
        "__import__",
        "powershell",
        "cmd.exe",
        "/bin/sh",
        "xp_cmdshell",
    )

    def __init__(
        self,
        *,
        config: GuardConfig | None = None,
        ml_engine: MLEngine | None = None,
        synaptic_layer: SynapticLayer | None = None,
        native_runtime=None,
    ):
        self.config = config or GuardConfig()
        self.ml_engine = ml_engine or MLEngine(enabled=False)
        self.synaptic_layer = synaptic_layer or SynapticLayer(enabled=False)
        self.native_runtime = native_runtime

    def inspect(
        self,
        request,
        *,
        route=None,
        path_params: dict[str, str] | None = None,
        validation_issues: list[dict[str, Any]] | None = None,
    ) -> GuardReport:
        started = perf_counter()
        if not self.config.enabled:
            return GuardReport(enabled=False, duration_ms=0.0)

        validation_issues = list(validation_issues or [])
        profile = self._profile(request, route=route, path_params=path_params)
        signals: list[GuardSignal] = []

        signals.extend(self._signals_from_validation(validation_issues))
        signals.extend(self._profile_signals(profile))
        signals.extend(self._payload_signals(request, profile))
        signals.extend(self._header_signals(request, profile))
        signals.extend(self._shape_signals(profile))

        synaptic_payload = None
        synaptic_decision = self._run_synaptic(request)
        if synaptic_decision is not None:
            synaptic_payload = synaptic_decision.to_dict()
            signals.extend(self._signals_from_synaptic(synaptic_decision))

        ml_payload = None
        if self.ml_engine.enabled:
            ml_result = self.ml_engine.analyze(request)
            ml_payload = ml_result.to_dict()
            signals.extend(self._signals_from_ml(ml_result))

        native_payload = self._native_scan(request)
        if native_payload is not None:
            signals.extend(self._signals_from_native(native_payload))
        native_validation = self._native_validation(request)
        if native_validation is not None:
            signals.extend(self._signals_from_native_validation(native_validation))
            if native_payload is None:
                native_payload = {}
            native_payload["validation"] = native_validation

        risk_score = self._score(profile, signals, validation_issues, synaptic_payload, ml_payload, native_payload)
        policy = self._policy(risk_score, profile, signals, native_payload)
        action = self._action(risk_score, signals, policy, validation_issues)
        confidence = self._confidence(risk_score, signals, synaptic_payload, ml_payload, native_payload)
        last_error = self._last_error(action, signals, validation_issues, policy)

        duration = round((perf_counter() - started) * 1000, 3)
        return GuardReport(
            enabled=True,
            action=action,
            risk_score=round(risk_score, 4),
            confidence=round(confidence, 4),
            duration_ms=duration,
            profile=profile,
            signals=self._dedupe_signals(signals),
            validation_issues=validation_issues,
            synaptic=synaptic_payload,
            ml=ml_payload,
            native=native_payload,
            policy=policy,
            last_error=last_error,
        )

    def _profile(self, request, *, route=None, path_params: dict[str, str] | None = None) -> RequestProfile:
        raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
        body_text = raw[:4096].decode("utf-8", errors="ignore")
        intent = infer_intent(request.path, request.method, body_text)
        route_name = getattr(route, "name", None) if route is not None else None
        route_sensitivity = self._route_sensitivity(request.path, request.method, route=route)
        shape = self._shape(request.body, path_params or {})
        fingerprint = self._fingerprint(request, raw)
        return RequestProfile(
            method=request.method,
            path=request.path,
            intent=intent,
            route_name=route_name,
            route_sensitivity=route_sensitivity,
            body_bytes=len(raw),
            query_count=len(request.query or {}),
            header_count=len(request.headers or {}),
            content_type=request.headers.get("Content-Type", ""),
            user_agent=request.headers.get("User-Agent", ""),
            fingerprint=fingerprint,
            shape=shape,
        )

    def _route_sensitivity(self, path: str, method: str, *, route=None) -> int:
        lowered = (path or "").lower()
        score = 0
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            score += 1
        if any(token in lowered for token in self.ADMIN_HINTS):
            score += 3
        if any(token in lowered for token in self.AUTH_HINTS):
            score += 2
        if any(token in lowered for token in self.PAYMENT_HINTS):
            score += 2
        if any(token in lowered for token in self.TOOL_HINTS):
            score += 3
        if any(token in lowered for token in self.FILE_HINTS):
            score += 1
        if getattr(route, "auth", False):
            score += 1
        if getattr(route, "native", None):
            score += 1
        if getattr(route, "ml_check", False):
            score += 1
        return min(score, 8)

    def _shape(self, body: Any, path_params: dict[str, str]) -> dict[str, Any]:
        stats = {
            "body_type": self._type_name(body),
            "path_params": sorted(path_params),
            "max_depth": 0,
            "object_count": 0,
            "array_count": 0,
            "string_count": 0,
            "number_count": 0,
            "boolean_count": 0,
            "null_count": 0,
            "max_string_length": 0,
            "total_keys": 0,
        }
        self._walk_shape(body, stats, depth=0)
        return stats

    def _walk_shape(self, value: Any, stats: dict[str, Any], *, depth: int):
        stats["max_depth"] = max(stats["max_depth"], depth)
        if value is None:
            stats["null_count"] += 1
        elif isinstance(value, bool):
            stats["boolean_count"] += 1
        elif isinstance(value, int | float):
            stats["number_count"] += 1
        elif isinstance(value, str):
            stats["string_count"] += 1
            stats["max_string_length"] = max(stats["max_string_length"], len(value))
        elif isinstance(value, list):
            stats["array_count"] += 1
            for item in value[: self.config.max_array_length + 1]:
                self._walk_shape(item, stats, depth=depth + 1)
        elif isinstance(value, dict):
            stats["object_count"] += 1
            stats["total_keys"] += len(value)
            for item in list(value.values())[: self.config.max_object_keys + 1]:
                self._walk_shape(item, stats, depth=depth + 1)

    def _signals_from_validation(self, issues: list[dict[str, Any]]) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        for issue in issues:
            code = str(issue.get("code") or "VALIDATION_ERROR")
            severity = "high" if code in {"OBJECT_TOO_WIDE", "ARRAY_TOO_LONG", "MAX_DEPTH"} else "medium"
            signals.append(
                GuardSignal(
                    code=f"validation:{code.lower()}",
                    message=str(issue.get("message") or "Validation issue"),
                    kind=GuardSignalKind.DATA,
                    severity=severity,
                    score=0.08 if severity == "medium" else 0.16,
                    where=issue.get("where"),
                    hint=issue.get("hint"),
                    evidence={key: value for key, value in issue.items() if key not in {"message", "hint"}},
                )
            )
        return signals

    def _profile_signals(self, profile: RequestProfile) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        if profile.route_sensitivity >= 5:
            signals.append(
                GuardSignal(
                    "route:sensitive",
                    "Request targets a sensitive route family.",
                    GuardSignalKind.SECURITY,
                    "medium",
                    0.09,
                    "path",
                    "Use auth, validation and rate limits on this route.",
                    {"route_sensitivity": profile.route_sensitivity, "intent": profile.intent},
                )
            )
        if profile.body_bytes > self.config.max_body_size:
            signals.append(
                GuardSignal(
                    "body:too_large",
                    "Request body is larger than the configured guard limit.",
                    GuardSignalKind.DATA,
                    "critical",
                    0.34,
                    "body",
                    "Reduce payload size or raise max_body_size intentionally.",
                    {"body_bytes": profile.body_bytes, "max_body_size": self.config.max_body_size},
                )
            )
        elif profile.body_bytes > max(1, self.config.max_body_size // 2):
            signals.append(
                GuardSignal(
                    "body:large",
                    "Request body is approaching the configured guard limit.",
                    GuardSignalKind.DATA,
                    "low",
                    0.05,
                    "body",
                    evidence={"body_bytes": profile.body_bytes, "max_body_size": self.config.max_body_size},
                )
            )
        if profile.query_count >= 12:
            signals.append(
                GuardSignal(
                    "query:many_params",
                    "Request has unusually many query parameters.",
                    GuardSignalKind.ANOMALY,
                    "medium",
                    0.08,
                    "query",
                    "Collapse filters into a JSON body or reduce query fanout.",
                    {"query_count": profile.query_count},
                )
            )
        return signals

    def _payload_signals(self, request, profile: RequestProfile) -> list[GuardSignal]:
        raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
        text = raw[:16384].decode("utf-8", errors="ignore").lower()
        combined = f"{profile.path.lower()} {text}"
        signals: list[GuardSignal] = []
        token_groups = {
            "secret:exposed": self.SECRET_TOKENS,
            "ssrf:probe": self.SSRF_TOKENS,
            "code:execution_token": self.CODE_TOKENS,
            "file:dangerous_extension": self.HIGH_RISK_EXTENSIONS,
        }
        for code, tokens in token_groups.items():
            matched = [token for token in tokens if token in combined]
            if not matched:
                continue
            severity = "critical" if code in {"ssrf:probe", "code:execution_token"} else "high"
            signals.append(
                GuardSignal(
                    code,
                    f"Payload contains {code.split(':', 1)[1].replace('_', ' ')} signal.",
                    GuardSignalKind.SECURITY,
                    severity,
                    0.22 if severity == "critical" else 0.16,
                    "body",
                    self._hint_for_code(code),
                    {"matched": matched[:8]},
                )
            )
        if text.count("{") + text.count("[") > 500:
            signals.append(
                GuardSignal(
                    "json:structure_heavy",
                    "Payload has an unusually dense JSON structure.",
                    GuardSignalKind.ANOMALY,
                    "medium",
                    0.08,
                    "body",
                    "Check for generated or abusive JSON before accepting it.",
                    {"brackets": text.count("{") + text.count("[")},
                )
            )
        return signals

    def _header_signals(self, request, profile: RequestProfile) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        if not profile.user_agent:
            signals.append(
                GuardSignal(
                    "headers:missing_user_agent",
                    "Request is missing User-Agent.",
                    GuardSignalKind.BOT,
                    "low",
                    0.05,
                    "headers.User-Agent",
                )
            )
        if profile.method in {"POST", "PUT", "PATCH"} and profile.body_bytes and "application/json" not in profile.content_type.lower():
            signals.append(
                GuardSignal(
                    "headers:invalid_content_type",
                    "JSON body was sent without application/json content type.",
                    GuardSignalKind.DATA,
                    "high",
                    0.18,
                    "headers.Content-Type",
                    "Send Content-Type: application/json for JSON requests.",
                    {"received": profile.content_type or None},
                )
            )
        for key, value in (request.headers or {}).items():
            text = f"{key}: {value}"
            if "\r" in text or "\n" in text or "\x00" in text:
                signals.append(
                    GuardSignal(
                        "headers:control_character",
                        "Header contains a control character.",
                        GuardSignalKind.SECURITY,
                        "critical",
                        0.32,
                        f"headers.{key}",
                        "Reject or normalize the caller before it reaches business code.",
                    )
                )
        return signals

    def _shape_signals(self, profile: RequestProfile) -> list[GuardSignal]:
        shape = profile.shape
        signals: list[GuardSignal] = []
        if shape.get("max_depth", 0) > 10:
            signals.append(
                GuardSignal(
                    "shape:deep_json",
                    "JSON body is nested deeply.",
                    GuardSignalKind.ANOMALY,
                    "medium",
                    0.1,
                    "body",
                    "Deep JSON can trigger expensive validation and parser paths.",
                    {"max_depth": shape.get("max_depth")},
                )
            )
        if shape.get("max_string_length", 0) > self.config.max_string_length:
            signals.append(
                GuardSignal(
                    "shape:string_too_long",
                    "JSON body contains a very long string.",
                    GuardSignalKind.DATA,
                    "high",
                    0.18,
                    "body",
                    "Use file streaming for large blobs instead of inline JSON strings.",
                    {"max_string_length": shape.get("max_string_length")},
                )
            )
        if shape.get("total_keys", 0) > self.config.max_object_keys * 2:
            signals.append(
                GuardSignal(
                    "shape:wide_json",
                    "JSON body contains a very wide object graph.",
                    GuardSignalKind.ANOMALY,
                    "medium",
                    0.1,
                    "body",
                    "Split or page the payload before sending it to this route.",
                    {"total_keys": shape.get("total_keys")},
                )
            )
        return signals

    def _run_synaptic(self, request) -> SynapticDecision | None:
        if not self.synaptic_layer or not self.synaptic_layer.enabled:
            return None
        try:
            return self.synaptic_layer.analyze(request)
        except Exception as exc:
            return SynapticDecision(
                0.2,
                "observe",
                [f"synaptic_error:{exc.__class__.__name__}"],
                engine="synaptic-error",
            )

    def _native_scan(self, request) -> dict[str, Any] | None:
        if not self.native_runtime or not getattr(self.native_runtime, "available", False):
            return None
        try:
            raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
            return self.native_runtime.security_scan(
                request.method,
                request.path,
                content_type=request.headers.get("Content-Type", ""),
                body_size=len(raw),
                max_body_size=self.config.max_body_size,
                payload=raw[:8192].decode("utf-8", errors="ignore"),
            )
        except Exception as exc:
            return {"ok": False, "engine": "native-error", "error": {"type": exc.__class__.__name__, "message": str(exc)}}

    def _native_validation(self, request) -> dict[str, Any] | None:
        if not self.native_runtime or not getattr(self.native_runtime, "available", False):
            return None
        try:
            raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
            if not raw:
                return None
            return self.native_runtime.validation_scan(
                raw,
                max_depth=12,
                max_string_length=self.config.max_string_length,
                max_array_length=self.config.max_array_length,
                max_object_keys=self.config.max_object_keys,
            )
        except Exception as exc:
            return {"ok": False, "engine": "native-validation-error", "error": {"type": exc.__class__.__name__, "message": str(exc)}}

    def _signals_from_synaptic(self, decision: SynapticDecision) -> list[GuardSignal]:
        signals = [
            GuardSignal(
                f"synaptic:{item}",
                f"Synaptic layer reported {item}.",
                GuardSignalKind.POLICY,
                "high" if decision.decision == "block" else "medium",
                0.12 if decision.decision == "block" else 0.06,
                evidence={"engine": decision.engine, "decision": decision.decision},
            )
            for item in decision.signals[:16]
        ]
        if decision.decision == "block":
            signals.append(
                GuardSignal(
                    "synaptic:block",
                    "Synaptic layer requested blocking the request.",
                    GuardSignalKind.POLICY,
                    "critical",
                    0.34,
                    hint="Inspect synaptic.signals for the exact reason.",
                    evidence=decision.to_dict(),
                )
            )
        return signals

    def _signals_from_ml(self, ml_result) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        if ml_result.action in {"challenge", "block"}:
            signals.append(
                GuardSignal(
                    f"ml:{ml_result.action}",
                    f"ML engine requested {ml_result.action}.",
                    GuardSignalKind.POLICY,
                    "critical" if ml_result.action == "block" else "high",
                    0.28 if ml_result.action == "block" else 0.16,
                    evidence={"risk_score": ml_result.risk_score, "bot_score": ml_result.bot_score, "intent": ml_result.intent},
                )
            )
        for reason in ml_result.reasons[:16]:
            signals.append(
                GuardSignal(
                    f"ml:reason:{reason}",
                    f"ML engine reason: {reason}.",
                    GuardSignalKind.ANOMALY,
                    "medium",
                    0.05,
                    evidence={"intent": ml_result.intent},
                )
            )
        return signals

    def _signals_from_native(self, native: dict[str, Any]) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        if native.get("error"):
            signals.append(
                GuardSignal(
                    "native:error",
                    "Native guard failed and Python fallback continued.",
                    GuardSignalKind.SYSTEM,
                    "medium",
                    0.04,
                    hint="Rebuild the native runtime if this persists.",
                    evidence=native.get("error") or {},
                )
            )
            return signals
        if native.get("allowed") is False:
            signals.append(
                GuardSignal(
                    "native:blocked",
                    "Native scanner marked the request as not allowed.",
                    GuardSignalKind.NATIVE,
                    "critical",
                    0.3,
                    evidence={"risk_score": native.get("risk_score"), "fast_flags": native.get("fast_flags")},
                )
            )
        for item in (native.get("signals") or native.get("reasons") or [])[:16]:
            signals.append(
                GuardSignal(
                    f"native:{item}",
                    f"Native scanner reported {item}.",
                    GuardSignalKind.NATIVE,
                    "high",
                    0.08,
                    evidence={"engine": native.get("engine", "native-security")},
                )
            )
        return signals

    def _signals_from_native_validation(self, native_validation: dict[str, Any]) -> list[GuardSignal]:
        signals: list[GuardSignal] = []
        if native_validation.get("error"):
            signals.append(
                GuardSignal(
                    "native_validation:error",
                    "Native validation shield failed and Python validation continued.",
                    GuardSignalKind.SYSTEM,
                    "low",
                    0.03,
                    evidence=native_validation.get("error") or {},
                )
            )
            return signals
        if native_validation.get("ok", True):
            return signals
        for item in (native_validation.get("signals") or [])[:16]:
            severity = "critical" if item in {"binary_payload", "control_character", "unbalanced_json"} else "high"
            signals.append(
                GuardSignal(
                    f"native_validation:{item}",
                    f"Native validation shield reported {item}.",
                    GuardSignalKind.NATIVE,
                    severity,
                    0.18 if severity == "critical" else 0.1,
                    "body",
                    "Fix payload shape before it reaches Python validation and route code.",
                    {"engine": native_validation.get("engine"), "stats": native_validation.get("stats", {})},
                )
            )
        return signals

    def _score(
        self,
        profile: RequestProfile,
        signals: list[GuardSignal],
        validation_issues: list[dict[str, Any]],
        synaptic_payload: dict[str, Any] | None,
        ml_payload: dict[str, Any] | None,
        native_payload: dict[str, Any] | None,
    ) -> float:
        score = 0.03
        score += min(0.14, profile.route_sensitivity * 0.025)
        if profile.body_bytes:
            score += min(0.12, log10(max(10, profile.body_bytes)) / 80)
        score += min(0.24, sum(max(0.0, signal.score) for signal in signals))
        score += min(0.16, len(validation_issues) * 0.035)
        if synaptic_payload:
            score = max(score, float(synaptic_payload.get("risk_score", 0.0)))
        if ml_payload:
            score = max(score, float(ml_payload.get("risk_score", 0.0)))
            score += min(0.08, float(ml_payload.get("bot_score", 0.0)) * 0.08)
        if native_payload:
            score = max(score, float(native_payload.get("risk_score", 0.0) or 0.0))
        if any(signal.severity == "critical" for signal in signals):
            score += 0.16
        return min(0.99, score)

    def _policy(self, risk_score: float, profile: RequestProfile, signals: list[GuardSignal], native_payload: dict[str, Any] | None) -> dict[str, Any] | None:
        flags = int((native_payload or {}).get("fast_flags") or (native_payload or {}).get("flags") or 0)
        if not flags:
            critical_count = len([signal for signal in signals if signal.severity == "critical"])
            high_count = len([signal for signal in signals if signal.severity == "high"])
            flags = (1 << min(12, critical_count + high_count)) - 1 if critical_count or high_count else 0
        if self.native_runtime and getattr(self.native_runtime, "available", False):
            try:
                return self.native_runtime.policy_decision(risk_score, flags, profile.route_sensitivity)
            except Exception as exc:
                return {"action": "observe", "engine": "python-policy-after-native-error", "error": str(exc)}
        if risk_score >= self.config.block_threshold:
            action = "block"
        elif risk_score >= self.config.challenge_threshold:
            action = "challenge"
        elif risk_score >= self.config.observe_threshold:
            action = "observe"
        else:
            action = "allow"
        return {
            "action": action,
            "risk_score": round(risk_score, 4),
            "security_flags": flags,
            "route_sensitivity": profile.route_sensitivity,
            "engine": "python-guard-policy-v1",
        }

    def _action(self, risk_score: float, signals: list[GuardSignal], policy: dict[str, Any] | None, validation_issues: list[dict[str, Any]]) -> str:
        policy_action = (policy or {}).get("action")
        critical = any(signal.severity == "critical" for signal in signals)
        if self.config.strict_validation and validation_issues:
            return GuardAction.BLOCK if self.config.block_enabled else GuardAction.CHALLENGE
        if policy_action == "block" or risk_score >= self.config.block_threshold or critical:
            return GuardAction.BLOCK if self.config.block_enabled else GuardAction.CHALLENGE
        if policy_action == "challenge" or risk_score >= self.config.challenge_threshold:
            return GuardAction.CHALLENGE
        if policy_action == "observe" or risk_score >= self.config.observe_threshold or signals:
            return GuardAction.OBSERVE
        return GuardAction.ALLOW

    def _confidence(
        self,
        risk_score: float,
        signals: list[GuardSignal],
        synaptic_payload: dict[str, Any] | None,
        ml_payload: dict[str, Any] | None,
        native_payload: dict[str, Any] | None,
    ) -> float:
        confidence = 0.45 + min(0.24, len(signals) * 0.025) + min(0.18, risk_score * 0.18)
        if synaptic_payload:
            confidence += 0.06
        if ml_payload:
            confidence += 0.08
        if native_payload and not native_payload.get("error"):
            confidence += 0.08
        return min(0.99, confidence)

    def _last_error(self, action: str, signals: list[GuardSignal], validation_issues: list[dict[str, Any]], policy: dict[str, Any] | None) -> dict[str, Any] | None:
        if action == GuardAction.ALLOW and not validation_issues:
            return None
        if validation_issues:
            first = validation_issues[0]
            return {
                "code": first.get("code", "VALIDATION_ERROR"),
                "where": first.get("where"),
                "message": first.get("message", "Validation failed"),
                "hint": first.get("hint", "Fix the field reported in 'where'."),
            }
        if signals:
            signal = sorted(signals, key=lambda item: item.score, reverse=True)[0]
            return {
                "code": signal.code,
                "where": signal.where,
                "message": signal.message,
                "hint": signal.hint or "Inspect guard.signals for the reason.",
                "policy": (policy or {}).get("action"),
            }
        return None

    def _dedupe_signals(self, signals: list[GuardSignal]) -> list[GuardSignal]:
        deduped: dict[tuple[str, str | None], GuardSignal] = {}
        for signal in signals:
            key = (signal.code, signal.where)
            existing = deduped.get(key)
            if existing is None or signal.score > existing.score:
                deduped[key] = signal
        return sorted(deduped.values(), key=lambda item: item.score, reverse=True)

    def _fingerprint(self, request, raw: bytes) -> str:
        h = blake2b(digest_size=12)
        h.update((request.method or "").encode("utf-8", errors="ignore"))
        h.update(b"\0")
        h.update((request.path or "").encode("utf-8", errors="ignore"))
        h.update(b"\0")
        h.update(raw[:4096])
        return h.hexdigest()

    def _type_name(self, value: Any) -> str:
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

    def _hint_for_code(self, code: str) -> str:
        return {
            "secret:exposed": "Do not accept secrets in public request bodies unless this is an auth route.",
            "ssrf:probe": "Block internal network and metadata targets before making outbound requests.",
            "code:execution_token": "Never pass request content directly to shell, eval, subprocess or template execution.",
            "file:dangerous_extension": "Use an allowlist for upload extensions and stream files outside the web root.",
        }.get(code, "Inspect the matched evidence before allowing this request.")
