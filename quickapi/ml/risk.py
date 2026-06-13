from __future__ import annotations

from dataclasses import dataclass, field
from math import log10
from typing import Any


SUSPICIOUS_TOKENS = {
    "sql_injection": ("drop table", "union select", " or 1=1", "'--", "\"--"),
    "script_injection": ("<script", "javascript:", "onerror=", "onload="),
    "path_traversal": ("../", "..\\", "%2e", "%2f"),
    "abuse": ("bruteforce", "spam", "attack", "credential stuffing"),
}


@dataclass
class RequestFeatures:
    method: str
    path_depth: int
    body_bytes: int
    header_count: int
    query_count: int
    digit_ratio: float
    symbol_ratio: float
    suspicious_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path_depth": self.path_depth,
            "body_bytes": self.body_bytes,
            "header_count": self.header_count,
            "query_count": self.query_count,
            "digit_ratio": round(self.digit_ratio, 4),
            "symbol_ratio": round(self.symbol_ratio, 4),
            "suspicious_hits": list(self.suspicious_hits),
        }


def extract_features(request) -> RequestFeatures:
    raw = request.raw_body or str(request.body or "").encode("utf-8", errors="ignore")
    text = raw[:8192].decode("utf-8", errors="ignore").lower()
    combined = f"{request.path.lower()} {text}"
    chars = max(1, len(combined))
    suspicious_hits = []
    for group, tokens in SUSPICIOUS_TOKENS.items():
        if any(token in combined for token in tokens):
            suspicious_hits.append(group)
    return RequestFeatures(
        method=request.method,
        path_depth=len([part for part in request.path.split("/") if part]),
        body_bytes=len(raw),
        header_count=len(request.headers),
        query_count=len(request.query),
        digit_ratio=sum(ch.isdigit() for ch in combined) / chars,
        symbol_ratio=sum(not ch.isalnum() and not ch.isspace() for ch in combined) / chars,
        suspicious_hits=suspicious_hits,
    )


def score_risk(features: RequestFeatures, intent: str) -> tuple[float, list[str]]:
    score = 0.04
    reasons: list[str] = []
    if intent in {"payment_attempt", "auth", "admin"}:
        score += 0.18
        reasons.append(f"sensitive_intent:{intent}")
    if features.method in {"POST", "PUT", "PATCH", "DELETE"}:
        score += 0.06
    if features.body_bytes > 1024 * 1024:
        score += min(0.18, log10(features.body_bytes / 1024) / 20)
        reasons.append("large_body")
    if features.path_depth >= 6:
        score += 0.08
        reasons.append("deep_path")
    if features.query_count >= 8:
        score += 0.08
        reasons.append("many_query_params")
    if features.digit_ratio > 0.45:
        score += 0.06
        reasons.append("high_digit_ratio")
    if features.symbol_ratio > 0.35:
        score += 0.08
        reasons.append("high_symbol_ratio")
    if features.suspicious_hits:
        score += 0.48 + (0.08 * min(3, len(features.suspicious_hits)))
        reasons.extend(features.suspicious_hits)
    return min(score, 0.99), reasons


def score_bot(features: RequestFeatures, headers) -> tuple[float, list[str]]:
    score = 0.02
    reasons: list[str] = []
    user_agent = headers.get("User-Agent", "")
    accept = headers.get("Accept", "")
    if not user_agent:
        score += 0.28
        reasons.append("missing_user_agent")
    if not accept:
        score += 0.08
        reasons.append("missing_accept")
    if features.header_count <= 2:
        score += 0.12
        reasons.append("low_header_count")
    if features.query_count >= 10:
        score += 0.08
    return min(score, 0.95), reasons
