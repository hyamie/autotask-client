"""Custom exception hierarchy for Autotask API errors."""


class AutotaskError(Exception):
    """Base exception for all Autotask client errors."""


class AutotaskAuthError(AutotaskError):
    """Authentication failed. Check credentials and API integration code.

    Note: Autotask returns HTTP 500 for invalid credentials, not 401.
    """


class AutotaskRateLimitError(AutotaskError):
    """Rate limit exceeded. 10k requests/hour shared across all integrations."""


class AutotaskNotFoundError(AutotaskError):
    """Entity or resource not found."""


class AutotaskValidationError(AutotaskError):
    """Request validation failed (missing fields, invalid values, etc.)."""


class AutotaskAPIError(AutotaskError):
    """Generic API error with status code and response details."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
