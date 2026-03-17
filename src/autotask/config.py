"""Configuration management for Autotask API credentials."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field


@dataclass
class AutotaskConfig:
    """Autotask API configuration.

    Create with explicit params or from environment variables via from_env().
    """

    username: str
    secret: str
    integration_code: str
    api_url: str | None = None
    resource_id: int | None = None
    lob_mappings: dict[str, int] = field(default_factory=dict)
    template_company_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> AutotaskConfig:
        """Load config from environment variables.

        Supports AUTOTASK_SECRET or AUTOTASK_SECRET_B64 (base64-encoded, for
        platforms like Vercel that mangle special characters).

        Raises:
            ValueError: If required environment variables are missing.
        """
        username = os.environ.get("AUTOTASK_USERNAME")
        if not username:
            raise ValueError("AUTOTASK_USERNAME environment variable is required")

        secret = os.environ.get("AUTOTASK_SECRET")
        secret_b64 = os.environ.get("AUTOTASK_SECRET_B64")
        if secret_b64 and not secret:
            secret = base64.b64decode(secret_b64).decode()
        if not secret:
            raise ValueError(
                "AUTOTASK_SECRET or AUTOTASK_SECRET_B64 environment variable is required"
            )

        integration_code = os.environ.get("AUTOTASK_INTEGRATION_CODE")
        if not integration_code:
            raise ValueError("AUTOTASK_INTEGRATION_CODE environment variable is required")

        api_url = os.environ.get("AUTOTASK_API_URL")
        resource_id_str = os.environ.get("AUTOTASK_RESOURCE_ID")
        resource_id = int(resource_id_str) if resource_id_str else None

        return cls(
            username=username,
            secret=secret,
            integration_code=integration_code,
            api_url=api_url,
            resource_id=resource_id,
        )

    def auth_headers(self) -> dict[str, str]:
        """Return the authentication headers for Autotask API requests."""
        return {
            "UserName": self.username,
            "Secret": self.secret,
            "ApiIntegrationCode": self.integration_code,
            "Content-Type": "application/json",
        }
