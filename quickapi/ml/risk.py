def score_risk(text: str) -> float:
    text = text.lower()
    suspicious = ["drop table", "bruteforce", "spam", "attack"]
    return 0.9 if any(token in text for token in suspicious) else 0.1
