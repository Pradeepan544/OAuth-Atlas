class AppError(Exception):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AppError):
    pass


class InvalidRequestError(AppError):
    pass


class ResearchIncompleteError(AppError):
    pass


class UpstreamServiceError(AppError):
    pass


class GuideValidationError(AppError):
    pass
