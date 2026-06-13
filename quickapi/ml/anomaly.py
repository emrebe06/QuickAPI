def detect_anomaly(features) -> tuple[bool, list[str]]:
    reasons = []
    if features.body_bytes > 10 * 1024 * 1024:
        reasons.append("very_large_body")
    if features.path_depth > 10:
        reasons.append("extreme_path_depth")
    if features.symbol_ratio > 0.5:
        reasons.append("symbol_heavy_payload")
    if len(features.suspicious_hits) >= 2:
        reasons.append("multiple_attack_patterns")
    return bool(reasons), reasons
