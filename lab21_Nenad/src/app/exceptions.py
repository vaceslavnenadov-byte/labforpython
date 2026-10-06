"""Централизованные исключения → единый формат ответа {"error": CODE, "message": "..."}."""


class AppException(Exception):
    status_code = 400
    error = "BAD_REQUEST"

    def __init__(self, message: str, error: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error:
            self.error = error


class EntityNotFoundException(AppException):
    status_code = 404
    error = "NOT_FOUND"


class ValidationException(AppException):
    status_code = 422
    error = "VALIDATION_ERROR"


class BusinessRuleException(AppException):
    status_code = 409
    error = "BUSINESS_RULE_VIOLATION"


class AuthException(AppException):
    status_code = 401
    error = "UNAUTHORIZED"


class ForbiddenException(AppException):
    status_code = 403
    error = "FORBIDDEN"


class ExternalServiceException(AppException):
    status_code = 503
    error = "SERVICE_UNAVAILABLE"
