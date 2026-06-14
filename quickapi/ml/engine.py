from dataclasses import dataclass, field
from typing import Any

from quickapi.ml.anomaly import detect_anomaly
from quickapi.ml.intent import infer_intent
from quickapi.ml.model import LogisticRiskModel, RiskModel
from quickapi.ml.risk import extract_features, score_bot, score_risk


@dataclass
class MLResult:
    intent: str
    risk_score: float
    bot_score: float
    action: str
    anomaly: bool = False
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    model_score: float = 0.0
    model_name: str | None = None

    def to_dict(self):
        return {
            "intent": self.intent,
            "risk_score": self.risk_score,
            "bot_score": self.bot_score,
            "action": self.action,
            "anomaly": self.anomaly,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "features": dict(self.features),
            "model_score": self.model_score,
            "model_name": self.model_name,
        }


class MLEngine:
    def __init__(self, enabled: bool = False, model: RiskModel | None = None, model_path: str | None = None):
        self.enabled = enabled
        self.model = model or self._load_model(model_path) or LogisticRiskModel.default()

    def analyze(self, request) -> MLResult:
        if not self.enabled:
            return MLResult("unknown", 0.0, 0.0, "allow", confidence=0.0)

        raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
        body_text = raw[:2048].decode("utf-8", errors="ignore")
        intent = infer_intent(request.path, request.method, body_text)
        features = extract_features(request)
        risk, risk_reasons = score_risk(features, intent)
        bot, bot_reasons = score_bot(features, request.headers)
        anomaly, anomaly_reasons = detect_anomaly(features)
        if anomaly:
            risk = min(0.99, risk + 0.12)
        feature_payload = features.to_dict()
        feature_payload.update(
            {
                "intent": intent,
                "missing_user_agent": "missing_user_agent" in bot_reasons,
                "missing_accept": "missing_accept" in bot_reasons,
                "anomaly": anomaly,
            }
        )
        model_score = self.model.predict_proba(feature_payload) if self.model else 0.0
        risk = max(risk, model_score)

        action = self._policy(risk, bot, anomaly)
        confidence = min(0.99, 0.55 + (risk * 0.25) + (bot * 0.15) + (model_score * 0.1) + (0.05 if anomaly else 0.0))
        return MLResult(
            intent=intent,
            risk_score=round(risk, 4),
            bot_score=round(bot, 4),
            action=action,
            anomaly=anomaly,
            confidence=round(confidence, 4),
            reasons=risk_reasons + bot_reasons + anomaly_reasons,
            features=feature_payload,
            model_score=round(model_score, 4),
            model_name=getattr(self.model, "name", None),
        )

    def train(self, samples: list[dict[str, Any]], *, epochs: int = 50, learning_rate: float = 0.05):
        if not hasattr(self.model, "train"):
            raise RuntimeError("Configured model does not support training")
        self.model.train(samples, epochs=epochs, learning_rate=learning_rate)
        return self

    def save_model(self, path: str):
        if not hasattr(self.model, "save"):
            raise RuntimeError("Configured model does not support save_model")
        self.model.save(path)

    def model_info(self) -> dict[str, Any]:
        if hasattr(self.model, "to_dict"):
            return self.model.to_dict()
        return {"name": getattr(self.model, "name", self.model.__class__.__name__)}

    @staticmethod
    def _policy(risk: float, bot: float, anomaly: bool) -> str:
        if risk >= 0.9 or (risk >= 0.82 and anomaly):
            return "block"
        if risk >= 0.72 or bot >= 0.65 or anomaly:
            return "challenge"
        if risk >= 0.45:
            return "observe"
        return "allow"

    def _load_model(self, model_path: str | None):
        if not model_path:
            return None
        return LogisticRiskModel.load(model_path)
