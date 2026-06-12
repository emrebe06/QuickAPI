from quickapi.http.status import status_code_name
from quickapi.response.format import format_error, format_success
from quickapi.response.json_response import JSONResponse


class ResponseFactory:
    def ok(self, data=None, message: str = "Success", status: int = 200):
        return format_success(data=data, status=status, code=status_code_name(status), message=message)

    def created(self, data=None, message: str = "Created"):
        return self.ok(data=data, message=message, status=201)

    def accepted(self, data=None, message: str = "Accepted"):
        return self.ok(data=data, message=message, status=202)

    def no_content(self, message: str = "No content"):
        return self.ok(data=None, message=message, status=204)

    def error(self, status: int, code: str, message: str, detail=None, error_type: str = "api_error"):
        return format_error(status=status, code=code, message=message, detail=detail, error_type=error_type)

    def bad_request(self, message: str = "Bad request", detail=None):
        return self.error(400, "BAD_REQUEST", message, detail)

    def unauthorized(self, message: str = "Unauthorized", detail=None):
        return self.error(401, "UNAUTHORIZED", message, detail)

    def payment_required(self, message: str = "Payment required", detail=None):
        return self.error(402, "PAYMENT_REQUIRED", message, detail)

    def forbidden(self, message: str = "Forbidden", detail=None):
        return self.error(403, "FORBIDDEN", message, detail)

    def not_found(self, message: str = "Not found", detail=None):
        return self.error(404, "NOT_FOUND", message, detail, "route_error")

    def method_not_allowed(self, message: str = "Method not allowed", detail=None):
        return self.error(405, "METHOD_NOT_ALLOWED", message, detail, "route_error")

    def conflict(self, message: str = "Conflict", detail=None):
        return self.error(409, "CONFLICT", message, detail)

    def unsupported_media_type(self, message: str = "Unsupported media type", detail=None):
        return self.error(415, "UNSUPPORTED_MEDIA_TYPE", message, detail)

    def validation(self, message: str = "Validation error", detail=None):
        return self.error(422, "VALIDATION_ERROR", message, detail, "validation_error")

    def too_many_requests(self, message: str = "Too many requests", detail=None):
        return self.error(429, "TOO_MANY_REQUESTS", message, detail, "rate_limit_error")

    def server_error(self, message: str = "Internal server error", detail=None):
        return self.error(500, "INTERNAL_SERVER_ERROR", message, detail, "server_error")

    def bad_gateway(self, message: str = "Bad gateway", detail=None):
        return self.error(502, "BAD_GATEWAY", message, detail)

    def service_unavailable(self, message: str = "Service unavailable", detail=None):
        return self.error(503, "SERVICE_UNAVAILABLE", message, detail)

    def timeout(self, message: str = "Gateway timeout", detail=None):
        return self.error(504, "GATEWAY_TIMEOUT", message, detail, "gateway_error")

    def json(self, body: dict):
        return JSONResponse(body=body, status=body.get("status", 200))


q = ResponseFactory()
