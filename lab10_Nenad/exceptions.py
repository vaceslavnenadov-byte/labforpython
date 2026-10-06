class ApiError(Exception):
    """Ошибка, которая превращается в HTTP-ответ единого формата."""
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code

    def to_dict(self) -> dict:
        return {"error": self.message, "code": self.code}


class ValidationError(ApiError):
    status_code = 400
    code = "VALIDATION_ERROR"


class TrainNotFoundError(ApiError):
    status_code = 404
    code = "TRAIN_NOT_FOUND"

    def __init__(self, train_id: int):
        super().__init__(f"Train {train_id} not found")


class ConflictError(ApiError):
    status_code = 409
    code = "CONFLICT"
