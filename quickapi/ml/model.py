from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import exp
from pathlib import Path
from typing import Any, Protocol


class RiskModel(Protocol):
    name: str

    def predict_proba(self, features: dict[str, Any]) -> float:
        ...


@dataclass
class LogisticRiskModel:
    name: str = "quickapi-logistic-risk-v1"
    weights: dict[str, float] = field(default_factory=dict)
    bias: float = -2.2
    trained_samples: int = 0

    @classmethod
    def default(cls):
        return cls(
            weights={
                "body_kb": 0.035,
                "header_count": -0.025,
                "query_count": 0.055,
                "path_depth": 0.07,
                "digit_ratio": 0.45,
                "symbol_ratio": 0.85,
                "suspicious_count": 1.35,
                "is_mutating": 0.22,
                "missing_user_agent": 0.55,
                "missing_accept": 0.18,
                "sensitive_intent": 0.4,
                "anomaly": 0.75,
            },
            bias=-2.15,
        )

    def predict_proba(self, features: dict[str, Any]) -> float:
        x = self._vector(features)
        z = self.bias
        for name, value in x.items():
            z += self.weights.get(name, 0.0) * value
        return round(1.0 / (1.0 + exp(-max(-32.0, min(32.0, z)))), 6)

    def train(self, samples: list[dict[str, Any]], *, epochs: int = 50, learning_rate: float = 0.05, l2: float = 0.0005):
        for _ in range(max(1, epochs)):
            for sample in samples:
                label = 1.0 if sample.get("label") in {1, True, "abuse", "block", "bad"} else 0.0
                features = sample.get("features") or sample
                x = self._vector(features)
                pred = self.predict_proba(features)
                error = pred - label
                self.bias -= learning_rate * error
                for name, value in x.items():
                    current = self.weights.get(name, 0.0)
                    self.weights[name] = current - learning_rate * ((error * value) + (l2 * current))
        self.trained_samples += len(samples)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weights": dict(self.weights),
            "bias": self.bias,
            "trained_samples": self.trained_samples,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(
            name=data.get("name", "quickapi-logistic-risk-v1"),
            weights={str(key): float(value) for key, value in (data.get("weights") or {}).items()},
            bias=float(data.get("bias", -2.2)),
            trained_samples=int(data.get("trained_samples", 0)),
        )

    def save(self, path: str | Path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def _vector(self, features: dict[str, Any]) -> dict[str, float]:
        suspicious = features.get("suspicious_hits") or []
        method = str(features.get("method", "GET")).upper()
        intent = str(features.get("intent", ""))
        return {
            "body_kb": min(2048.0, float(features.get("body_bytes", 0) or 0) / 1024.0),
            "header_count": min(64.0, float(features.get("header_count", 0) or 0)),
            "query_count": min(64.0, float(features.get("query_count", 0) or 0)),
            "path_depth": min(32.0, float(features.get("path_depth", 0) or 0)),
            "digit_ratio": float(features.get("digit_ratio", 0.0) or 0.0),
            "symbol_ratio": float(features.get("symbol_ratio", 0.0) or 0.0),
            "suspicious_count": min(16.0, float(len(suspicious))),
            "is_mutating": 1.0 if method in {"POST", "PUT", "PATCH", "DELETE"} else 0.0,
            "missing_user_agent": 1.0 if features.get("missing_user_agent") else 0.0,
            "missing_accept": 1.0 if features.get("missing_accept") else 0.0,
            "sensitive_intent": 1.0 if intent in {"payment_attempt", "auth", "admin"} else 0.0,
            "anomaly": 1.0 if features.get("anomaly") else 0.0,
        }
