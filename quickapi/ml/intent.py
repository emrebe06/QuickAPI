def infer_intent(path: str) -> str:
    path = path.lower()
    if "cart" in path:
        return "cart"
    if "payment" in path or "checkout" in path:
        return "payment"
    if "login" in path or "auth" in path:
        return "auth"
    return "generic"
