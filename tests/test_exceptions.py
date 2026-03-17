"""Tests for custom exception hierarchy."""

from autotask.exceptions import (
    AutotaskAPIError,
    AutotaskAuthError,
    AutotaskError,
    AutotaskNotFoundError,
    AutotaskRateLimitError,
    AutotaskValidationError,
)


def test_exception_hierarchy() -> None:
    """All exceptions inherit from AutotaskError."""
    assert issubclass(AutotaskAuthError, AutotaskError)
    assert issubclass(AutotaskRateLimitError, AutotaskError)
    assert issubclass(AutotaskNotFoundError, AutotaskError)
    assert issubclass(AutotaskValidationError, AutotaskError)
    assert issubclass(AutotaskAPIError, AutotaskError)


def test_api_error_stores_details() -> None:
    """AutotaskAPIError stores status code and response body."""
    err = AutotaskAPIError("Something failed", status_code=500, response_body='{"errors":["bad"]}')
    assert err.status_code == 500
    assert err.response_body == '{"errors":["bad"]}'
    assert "Something failed" in str(err)
