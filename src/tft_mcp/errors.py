"""Structured adapter errors shared by concrete simulator helpers."""


class SessionError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def result(self):
        return {"code": self.code, "message": str(self), "details": self.details}
