class QuickAPIError(Exception):
    def __init__(self, message: str, status: int = 500, code: str = "INTERNAL_SERVER_ERROR", detail=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.detail = detail
