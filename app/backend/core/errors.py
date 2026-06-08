"""Domain errors. The FastAPI handler maps these to HTTP status + the { error } envelope."""


class AppError(Exception):
    status = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status = 404
    code = "not_found"


class ValidationError(AppError):
    status = 400
    code = "validation_error"


class ConflictError(AppError):
    status = 409
    code = "conflict"
