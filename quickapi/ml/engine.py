from dataclasses import dataclass


@dataclass
class MLResult:
    intent: str
    risk_score: float
    bot_score: float
    action: str

    def to_dict(self):
        return {
            "intent": self.intent,
            "risk_score": self.risk_score,
            "bot_score": self.bot_score,
            "action": self.action,
        }


class MLEngine:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def analyze(self, request) -> MLResult:
        if not self.enabled:
            return MLResult("unknown", 0.0, 0.0, "allow")

        path = request.path.lower()
        body_text = str(request.body or {}).lower()
        intent = self._intent(path)
        risk = 0.08
        bot = 0.02
        if "payment" in path or "checkout" in path:
            risk = 0.32
        if any(word in body_text for word in ["attack", "spam", "bruteforce", "drop table"]):
            risk = 0.92
            bot = 0.57
        action = "challenge" if risk >= 0.85 else "allow"
        return MLResult(intent, risk, bot, action)

    @staticmethod
    def _intent(path: str) -> str:
        if "cart" in path and "add" in path:
            return "cart_add"
        if "payment" in path or "checkout" in path:
            return "payment_attempt"
        if "login" in path:
            return "login"
        return "api_request"
