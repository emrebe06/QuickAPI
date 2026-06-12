from datetime import datetime


class AccessLogger:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def startup(self, name: str, host: str, port: int):
        if self.enabled:
            print(f"[quickapi] {name} listening on http://{host}:{port}", flush=True)

    def request(self, method: str, path: str, response, ip: str):
        if not self.enabled:
            return
        body = response.to_dict()
        if isinstance(body, dict):
            status = body.get("status", response.status)
            code = body.get("code", "-")
            meta = body.get("meta", {})
            request_id = meta.get("request_id", "-")
            time_ms = meta.get("time_ms", 0)
            error = body.get("error")
        else:
            status = response.status
            code = "RAW"
            request_id = "-"
            time_ms = 0
            error = None

        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"[quickapi] {stamp} {ip} {method} {path} -> {status} {code} {time_ms}ms req={request_id}", flush=True)
        if error:
            print(f"[quickapi] error type={error.get('type')} detail={error.get('detail')}", flush=True)

    def invalid_json(self, method: str, path: str, ip: str, message: str):
        if self.enabled:
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"[quickapi] {stamp} {ip} {method} {path} -> 400 BAD_REQUEST error={message}", flush=True)

    def shutdown(self, name: str, message: str):
        if self.enabled:
            print(f"[quickapi] {name}: {message}", flush=True)
