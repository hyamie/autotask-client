"""Shared test fixtures for autotask client tests."""

import pytest


@pytest.fixture
def autotask_creds() -> dict[str, str]:
    """Fake credentials for testing. Never hits real API."""
    return {
        "username": "test@example.com",
        "secret": "fake-secret-for-testing",
        "integration_code": "FAKE_CODE",
        "api_url": "https://webservices24.autotask.net",
    }
