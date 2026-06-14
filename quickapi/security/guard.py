from quickapi.response.factory import q
from quickapi.security.rate_limit import RateLimiter


class SecurityGuard:
    SUSPICIOUS_PATH_TOKENS = (
        "..",
        "%2e",
        "%2f",
        "\\",
        "\x00",
        "<script",
        "${",
        "/.env",
        "/wp-admin",
        "/phpmyadmin",
        "/server-status",
        "/actuator",
    )
    SUSPICIOUS_BODY_TOKENS = (
        "<script",
        "javascript:",
        "drop table",
        "union select",
        "xp_cmdshell",
        "powershell",
        "cmd.exe",
        "/bin/sh",
        "169.254.169.254",
        "metadata.google.internal",
        "file://",
        "../",
        "..\\",
        "\x00",
    )
    SUSPICIOUS_HEADER_TOKENS = ("\r", "\n", "\x00")

    def __init__(self, enabled: bool = False, max_body_size: int = 1024 * 1024):
        self.enabled = enabled
        self.max_body_size = max_body_size
        self.rate_limiter = RateLimiter()

    def check(self, request):
        if request.raw_body and len(request.raw_body) > self.max_body_size:
            return q.error(
                413,
                "PAYLOAD_TOO_LARGE",
                "Request body is too large",
                {
                    "where": "body",
                    "limit_bytes": self.max_body_size,
                    "received_bytes": len(request.raw_body),
                    "hint": "Reduce the JSON payload size or raise max_body_size.",
                },
            )
        if not self.enabled:
            return None
        suspicious = self._detect_suspicious_request(request)
        if suspicious:
            return q.bad_request("Suspicious request rejected", suspicious)
        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("Content-Type", "")
            if request.raw_body and "application/json" not in content_type.lower():
                return q.unsupported_media_type(
                    "JSON content-type required",
                    {
                        "where": "headers.Content-Type",
                        "received": content_type or None,
                        "expected": "application/json",
                        "hint": "Send JSON requests with Content-Type: application/json.",
                    },
                )
        if not self.rate_limiter.allow(request.ip):
            return q.too_many_requests(
                detail={
                    "where": "rate_limit",
                    "ip": request.ip,
                    "hint": "Slow down requests or use a less strict route rate limit.",
                }
            )
        return None

    def _detect_suspicious_request(self, request):
        lowered_path = request.path.lower()
        for token in self.SUSPICIOUS_PATH_TOKENS:
            if token in lowered_path:
                return {
                    "where": "path",
                    "value": request.path,
                    "matched": token,
                    "hint": "Do not send traversal, scanner probe, encoded slash/dot, script, or null-byte patterns in the path.",
                }

        for key, value in request.headers.items():
            text = f"{key}: {value}"
            if any(token in text for token in self.SUSPICIOUS_HEADER_TOKENS):
                return {
                    "where": f"headers.{key}",
                    "hint": "Header values cannot contain control characters.",
                }

        body_text = ""
        if request.raw_body:
            body_text = request.raw_body[:4096].decode("utf-8", errors="ignore").lower()
        else:
            body_text = str(request.body or "").lower()
        for token in self.SUSPICIOUS_BODY_TOKENS:
            if token in body_text:
                return {
                    "where": "body",
                    "matched": token,
                    "hint": "JSON body contains a blocked script, SQL, command, SSRF, traversal, or null-byte pattern.",
                }
        return None
