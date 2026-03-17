"""Tests for configuration management."""

import base64

import pytest

from autotask.config import AutotaskConfig


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config loads from environment variables."""
    monkeypatch.setenv("AUTOTASK_USERNAME", "user@example.com")
    monkeypatch.setenv("AUTOTASK_SECRET", "my-secret")
    monkeypatch.setenv("AUTOTASK_INTEGRATION_CODE", "CODE123")

    config = AutotaskConfig.from_env()
    assert config.username == "user@example.com"
    assert config.secret == "my-secret"
    assert config.integration_code == "CODE123"
    assert config.api_url is None


def test_config_from_env_base64_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config decodes base64 secret when AUTOTASK_SECRET_B64 is set."""
    encoded = base64.b64encode(b"my-secret").decode()
    monkeypatch.setenv("AUTOTASK_USERNAME", "user@example.com")
    monkeypatch.setenv("AUTOTASK_SECRET_B64", encoded)
    monkeypatch.setenv("AUTOTASK_INTEGRATION_CODE", "CODE123")

    config = AutotaskConfig.from_env()
    assert config.secret == "my-secret"


def test_config_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config raises when required vars are missing."""
    monkeypatch.delenv("AUTOTASK_USERNAME", raising=False)
    monkeypatch.delenv("AUTOTASK_SECRET", raising=False)
    monkeypatch.delenv("AUTOTASK_SECRET_B64", raising=False)
    monkeypatch.delenv("AUTOTASK_INTEGRATION_CODE", raising=False)

    with pytest.raises(ValueError, match="AUTOTASK_USERNAME"):
        AutotaskConfig.from_env()


def test_config_explicit_params() -> None:
    """Config accepts explicit parameters."""
    config = AutotaskConfig(
        username="user@example.com",
        secret="secret",
        integration_code="CODE",
        api_url="https://webservices24.autotask.net",
    )
    assert config.api_url == "https://webservices24.autotask.net"


def test_config_auth_headers() -> None:
    """Config produces correct auth headers."""
    config = AutotaskConfig(
        username="user@example.com",
        secret="secret",
        integration_code="CODE",
    )
    headers = config.auth_headers()
    assert headers["UserName"] == "user@example.com"
    assert headers["Secret"] == "secret"
    assert headers["ApiIntegrationCode"] == "CODE"
    assert headers["Content-Type"] == "application/json"
