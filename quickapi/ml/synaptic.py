from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quickapi.ml.engine import MLEngine
from quickapi.ml.risk import extract_features, score_bot, score_risk
from quickapi.ml.intent import infer_intent


@dataclass
class SynapticDecision:
    risk_score: float
    decision: str
    signals: list[str] = field(default_factory=list)
    engine: str = "synaptic-v0-rule-native"
    ml: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    native_flags: int = 0
    route_sensitivity: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = {
            "risk_score": self.risk_score,
            "decision": self.decision,
            "signals": list(self.signals),
            "engine": self.engine,
        }
        if self.ml is not None:
            data["ml"] = self.ml
        if self.policy is not None:
            data["policy"] = self.policy
        if self.native_flags:
            data["native_flags"] = self.native_flags
        if self.route_sensitivity:
            data["route_sensitivity"] = self.route_sensitivity
        return data


class SynapticLayer:
    """Transparent rule-first request analysis with optional Python ML fallback."""

    def __init__(self, enabled: bool = False, ml_engine: MLEngine | None = None, native_runtime=None, max_body_size: int = 1024 * 1024):
        self.enabled = enabled
        self.ml_engine = ml_engine or MLEngine(enabled=False)
        self.native_runtime = native_runtime
        self.max_body_size = max_body_size

    def analyze(self, request) -> SynapticDecision:
        if not self.enabled:
            return SynapticDecision(0.0, "allow", [], engine="synaptic-disabled")

        native_decision = self._native_scan(request)
        if native_decision is not None and native_decision.decision == "block":
            return native_decision

        raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
        body_text = raw[:2048].decode("utf-8", errors="ignore")
        route_sensitivity = self._route_sensitivity(request)
        intent = infer_intent(request.path, request.method, body_text)
        features = extract_features(request)
        risk, risk_reasons = score_risk(features, intent)
        bot, bot_reasons = score_bot(features, request.headers)
        signals = list(dict.fromkeys(risk_reasons + bot_reasons + features.suspicious_hits))
        score = min(0.99, risk + (bot * 0.18))

        if score >= 0.90:
            decision = "block"
        elif score >= 0.72:
            decision = "allow_with_warning"
        elif score >= 0.45:
            decision = "observe"
        else:
            decision = "allow"

        ml_payload = None
        if self.ml_engine.enabled and decision in {"allow_with_warning", "block"}:
            ml_result = self.ml_engine.analyze(request)
            ml_payload = ml_result.to_dict()
            if ml_result.action == "block":
                decision = "block"
                score = max(score, ml_result.risk_score)
            signals = list(dict.fromkeys(signals + ml_result.reasons))

        if native_decision is not None:
            score = max(score, native_decision.risk_score)
            signals = list(dict.fromkeys(native_decision.signals + signals))
            engine = "synaptic-v0-native-python"
            route_sensitivity = max(route_sensitivity, native_decision.route_sensitivity)
            policy = self._native_policy(score, native_decision.native_flags, len(signals), route_sensitivity)
            if policy:
                engine = policy.get("engine", engine)
                policy_action = policy.get("action")
                if policy_action == "block":
                    decision = "block"
                elif policy_action == "challenge" and decision == "allow":
                    decision = "allow_with_warning"
        else:
            engine = "synaptic-v0-rule-native"
            policy = self._native_policy(score, 0, len(signals), route_sensitivity)
            if policy:
                engine = policy.get("engine", "synaptic-v0-policy-python")
                policy_action = policy.get("action")
                if policy_action == "block":
                    decision = "block"
                elif policy_action == "challenge" and decision == "allow":
                    decision = "allow_with_warning"
        return SynapticDecision(
            round(score, 4),
            decision,
            signals,
            engine=engine,
            ml=ml_payload,
            policy=policy,
            native_flags=native_decision.native_flags if native_decision is not None else 0,
            route_sensitivity=route_sensitivity,
        )

    def _native_scan(self, request) -> SynapticDecision | None:
        if not self.native_runtime or not getattr(self.native_runtime, "available", False):
            return None
        try:
            raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
            content_type = request.headers.get("Content-Type", "")
            result = self.native_runtime.security_scan(
                request.method,
                request.path,
                content_type=content_type,
                body_size=len(raw),
                max_body_size=self.max_body_size,
                payload=raw[:8192].decode("utf-8", errors="ignore"),
            )
        except Exception:
            return None
        score = float(result.get("risk_score", 0.0))
        signals = list(result.get("signals") or result.get("reasons") or [])
        native_flags = int(result.get("fast_flags") or result.get("flags") or 0)
        allowed = bool(result.get("allowed", True))
        if not allowed and score >= 0.80:
            decision = "block"
        elif score >= 0.72 or signals:
            decision = "allow_with_warning"
        elif score >= 0.45:
            decision = "observe"
        else:
            decision = "allow"
        return SynapticDecision(
            round(score, 4),
            decision,
            signals,
            engine=result.get("engine", "native-security-v1"),
            native_flags=native_flags,
            route_sensitivity=self._route_sensitivity(request),
        )

    def _native_policy(self, score: float, native_flags: int, signal_count: int, route_sensitivity: int) -> dict[str, Any] | None:
        if not self.native_runtime or not getattr(self.native_runtime, "available", False):
            return None
        try:
            fallback_flags = (1 << min(signal_count, 12)) - 1 if signal_count > 0 else 0
            return self.native_runtime.policy_decision(score, native_flags or fallback_flags, route_sensitivity)
        except Exception:
            return None

    def _route_sensitivity(self, request) -> int:
        path = (request.path or "").lower()
        method = (request.method or "GET").upper()
        score = 0
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            score += 1
        if any(token in path for token in ("/admin", "/auth", "/login", "/token", "/users", "/orders", "/checkout", "/payment")):
            score += 2
        if any(token in path for token in ("/quick/tools", "/quick/plugins", "/quick/agents", "/quick/llm", "/quick/webhooks")):
            score += 2
        if any(token in path for token in ("/internal", "/system", "/debug", "/database", "/db")):
            score += 2
        return min(score, 5)
