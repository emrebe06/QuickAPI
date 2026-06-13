INTENT_RULES = {
    "payment_attempt": ("payment", "checkout", "billing", "invoice", "card"),
    "auth": ("login", "logout", "auth", "token", "session", "password"),
    "upload": ("upload", "file", "media", "audio", "image"),
    "download": ("download", "static", "asset", "export"),
    "cart_add": ("cart/add", "basket/add"),
    "cart": ("cart", "basket"),
    "admin": ("admin", "dashboard", "manage"),
    "search": ("search", "query", "filter"),
}


def infer_intent(path: str, method: str = "GET", body_text: str = "") -> str:
    haystack = f"{method.lower()} {path.lower()} {body_text[:512].lower()}"
    for intent, tokens in INTENT_RULES.items():
        if any(token in haystack for token in tokens):
            return intent
    if method.upper() in {"POST", "PUT", "PATCH"}:
        return "write_request"
    return "read_request"
