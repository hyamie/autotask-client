# Autotask Python Client Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a pip-installable Python client library that encodes all Autotask REST API knowledge, with a thin CLI wrapper and docs that prevent Claude from ever relearning the API.

**Architecture:** Hybrid entity approach — hand-crafted classes for ~10 daily-driver entities (Tickets, Projects, Tasks, Companies, Resources, TimeEntries, Notes, Queues, Contacts, ConfigurationItems) with smart defaults and convenience methods, plus a generic fallback for all 211 entity types via metadata introspection. The library is the product; CLI is a thin Click wrapper. Attribute-based entity access: `client.tickets.get(12345)`.

**Tech Stack:** Python 3.12+, httpx (async HTTP), pydantic (entity models), tenacity (retry/backoff), click (CLI), pytest + pytest-asyncio (testing), hatch (build/packaging)

**PRD:** None (brainstorm doc at `.claude/plans/brainstorm-complete.md`)

**Confidence:** 0.90

**Decisions from plan review (Gemini):**
- Async-only (no sync wrapper) — consumers use `asyncio.run()` if needed
- LOB IDs and template company IDs are configurable via `AutotaskConfig`, NOT hardcoded
- GitHub repo created after Phase 6 (integration tests pass), local-only until then
- 1Password secret names looked up during integration test phase

**Estimated Sessions:** 6-7 sessions

**Source of truth for API behavior:** Your existing implementations at:
- `~/projects/active/pm/apps/web/src/lib/autotask-server.ts` (1150+ lines, most mature)
- `~/projects/active/1ife-os/dashboard/src/lib/autotask-actions.ts` (server actions pattern)
- `~/projects/active/1ife-os/dashboard/src/lib/autotask-types.ts` (picklist maps)

**Credentials:** 1Password ClaudeAgents vault. Env vars: `AUTOTASK_API_URL`, `AUTOTASK_USERNAME`, `AUTOTASK_SECRET`, `AUTOTASK_INTEGRATION_CODE`, `AUTOTASK_RESOURCE_ID`

---

## Phase 1: Project Scaffold + Core HTTP Client (Session 1) [COMPLETE]

Goal: Working project structure with auth, zone discovery, and a raw HTTP client that can make authenticated requests.

### Task 1: Project Scaffold [COMPLETE]

**Files:**
- Create: `pyproject.toml`
- Create: `src/autotask/__init__.py`
- Create: `src/autotask/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `CLAUDE.md`

**Step 1: Initialize git repo**

```bash
cd ~/projects/active/autotask-client
git init
```

**Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "autotask-client"
version = "0.1.0"
description = "Python client for the Autotask REST API"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "click>=8.0",
    "tenacity>=9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.34",
    "ruff>=0.8",
    "mypy>=1.13",
]

[project.scripts]
autotask = "autotask.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/autotask"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

**Step 3: Create src/autotask/__init__.py**

```python
"""Autotask REST API client library."""

__version__ = "0.1.0"
```

**Step 4: Create src/autotask/py.typed (empty marker file)**

**Step 5: Create tests/conftest.py**

```python
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
```

**Step 6: Create .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
```

**Step 7: Create CLAUDE.md**

```markdown
# autotask-client

Python client library for the Autotask REST API.

## Quick Reference

- **Package:** `src/autotask/`
- **Tests:** `tests/`
- **Install (dev):** `pip install -e ".[dev]"`
- **Run tests:** `pytest`
- **Lint:** `ruff check src/ tests/`
- **Type check:** `mypy src/`

## Architecture

- `client.py` — Core HTTP client (auth, zone discovery, rate limiting, pagination)
- `models/` — Pydantic entity models (hand-crafted daily-drivers + generic)
- `entities/` — Entity-specific logic (queries, convenience methods)
- `cli.py` — Click CLI (thin wrapper over library)
- `config.py` — Configuration management (env vars, 1Password)
- `exceptions.py` — Custom exception hierarchy

## API Gotchas (encode in code, not comments)

- Zone URL must be discovered first — GET /v1.0/zoneInformation?user=<email>
- Auth is header-based: UserName, Secret, ApiIntegrationCode
- Invalid creds return HTTP 500, not 401
- PATCH is safe (partial), PUT nulls unspecified fields — ALWAYS use PATCH
- Max 500 records per query, paginate with id > last_id
- 10k req/hour shared across ALL integrations
- Progressive throttling: 50% = 0.5s delay, 75% = 1s delay
- Silent permission failures return empty results, not errors
- UDFs missing from response when no values set
- Parent-child entities require parent ID in URL path
- 3 concurrent threads per endpoint max

## Test Strategy

- Unit tests mock httpx responses (never hit real API in CI)
- Integration tests (manual) use real creds from 1Password
- Use pytest-httpx for response mocking

## Credentials

1Password ClaudeAgents vault, or env vars:
AUTOTASK_API_URL, AUTOTASK_USERNAME, AUTOTASK_SECRET, AUTOTASK_INTEGRATION_CODE, AUTOTASK_RESOURCE_ID
```

**Step 8: Install in dev mode and verify**

```bash
cd ~/projects/active/autotask-client
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest --co  # collect tests, expect 0
```

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: project scaffold with pyproject.toml, src layout, dev tooling"
```

---

### Task 2: Configuration + Exceptions [COMPLETE]

**Files:**
- Create: `src/autotask/config.py`
- Create: `src/autotask/exceptions.py`
- Create: `tests/test_config.py`
- Create: `tests/test_exceptions.py`

**Step 1: Write failing tests for config**

```python
# tests/test_config.py
"""Tests for configuration management."""

import os
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
    assert config.api_url is None  # discovered later


def test_config_from_env_base64_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config decodes base64 secret when AUTOTASK_SECRET_B64 is set."""
    import base64
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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```
Expected: FAIL (module not found)

**Step 3: Write config implementation**

```python
# src/autotask/config.py
"""Configuration management for Autotask API credentials."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass


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
    lob_mappings: dict[str, int] | None = None  # e.g., {"CIT": 17, "CA": 18, "GA": 19, "NITH": 20}
    template_company_ids: list[int] | None = None  # e.g., [0, 264, 296] — filtered from queries

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
```

**Step 4: Write failing tests for exceptions**

```python
# tests/test_exceptions.py
"""Tests for custom exception hierarchy."""

from autotask.exceptions import (
    AutotaskError,
    AutotaskAuthError,
    AutotaskRateLimitError,
    AutotaskNotFoundError,
    AutotaskValidationError,
    AutotaskAPIError,
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
```

**Step 5: Write exceptions implementation**

```python
# src/autotask/exceptions.py
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
```

**Step 6: Run all tests**

```bash
pytest tests/test_config.py tests/test_exceptions.py -v
```
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/autotask/config.py src/autotask/exceptions.py tests/test_config.py tests/test_exceptions.py
git commit -m "feat: configuration management and exception hierarchy"
```

---

### Task 3: Core HTTP Client with Zone Discovery [COMPLETE]

**Files:**
- Create: `src/autotask/client.py`
- Create: `tests/test_client.py`

**Step 1: Write failing tests for zone discovery and basic requests**

```python
# tests/test_client.py
"""Tests for core HTTP client."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from autotask.client import AutotaskClient
from autotask.config import AutotaskConfig
from autotask.exceptions import AutotaskAuthError, AutotaskAPIError


@pytest.fixture
def config() -> AutotaskConfig:
    return AutotaskConfig(
        username="test@example.com",
        secret="test-secret",
        integration_code="TEST_CODE",
    )


@pytest.fixture
def config_with_url() -> AutotaskConfig:
    return AutotaskConfig(
        username="test@example.com",
        secret="test-secret",
        integration_code="TEST_CODE",
        api_url="https://webservices24.autotask.net",
    )


# --- Zone Discovery ---

async def test_zone_discovery(httpx_mock: HTTPXMock, config: AutotaskConfig) -> None:
    """Client discovers zone URL from Autotask API."""
    httpx_mock.add_response(
        url="https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation?user=test%40example.com",
        json={"url": "https://webservices24.autotask.net/atservicesrest/v1.0/"},
    )

    async with AutotaskClient(config) as client:
        assert client.base_url == "https://webservices24.autotask.net/atservicesrest/v1.0"


async def test_zone_discovery_skipped_when_url_provided(config_with_url: AutotaskConfig) -> None:
    """Client skips zone discovery when api_url is already set."""
    async with AutotaskClient(config_with_url) as client:
        assert "webservices24" in client.base_url


# --- GET Request ---

async def test_get_request(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """Client makes authenticated GET requests."""
    httpx_mock.add_response(
        url="https://webservices24.autotask.net/atservicesrest/v1.0/Tickets/entityInformation",
        json={"item": {"canCreate": True, "canQuery": True}},
    )

    async with AutotaskClient(config_with_url) as client:
        result = await client.get("Tickets/entityInformation")
        assert result["item"]["canCreate"] is True


async def test_get_sends_auth_headers(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """Client sends auth headers on every request."""
    httpx_mock.add_response(json={"item": {}})

    async with AutotaskClient(config_with_url) as client:
        await client.get("Tickets/entityInformation")

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["UserName"] == "test@example.com"
    assert request.headers["Secret"] == "test-secret"
    assert request.headers["ApiIntegrationCode"] == "TEST_CODE"


# --- POST Request ---

async def test_post_request(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """Client makes authenticated POST requests with JSON body."""
    httpx_mock.add_response(
        url="https://webservices24.autotask.net/atservicesrest/v1.0/Tickets/query",
        json={"items": [{"id": 1, "title": "Test Ticket"}]},
    )

    async with AutotaskClient(config_with_url) as client:
        result = await client.post("Tickets/query", json={"filter": [{"field": "status", "op": "eq", "value": 1}]})
        assert result["items"][0]["title"] == "Test Ticket"


# --- Error Handling ---

async def test_auth_error_on_500_with_auth_message(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """HTTP 500 with auth-related message raises AutotaskAuthError.

    Autotask returns 500 for invalid credentials, not 401.
    """
    httpx_mock.add_response(
        status_code=500,
        json={"errors": ["Invalid credentials"]},
    )

    async with AutotaskClient(config_with_url) as client:
        with pytest.raises(AutotaskAuthError):
            await client.get("Tickets")


async def test_generic_api_error(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """Non-auth errors raise AutotaskAPIError."""
    httpx_mock.add_response(
        status_code=400,
        json={"errors": ["Invalid filter"]},
    )

    async with AutotaskClient(config_with_url) as client:
        with pytest.raises(AutotaskAPIError) as exc_info:
            await client.get("Tickets")
        assert exc_info.value.status_code == 400
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```
Expected: FAIL (module not found)

**Step 3: Write client implementation**

```python
# src/autotask/client.py
"""Core HTTP client for Autotask REST API.

Handles authentication, zone discovery, rate limit awareness, and
request/response processing. This is the foundation everything else builds on.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

from autotask.config import AutotaskConfig
from autotask.exceptions import (
    AutotaskAPIError,
    AutotaskAuthError,
    AutotaskNotFoundError,
    AutotaskRateLimitError,
)

ZONE_DISCOVERY_URL = "https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation"

# Patterns in 500 responses that indicate auth failures
_AUTH_ERROR_PATTERNS = re.compile(
    r"(invalid credentials|authentication|unauthorized|login failed)",
    re.IGNORECASE,
)


class AutotaskClient:
    """Async HTTP client for the Autotask REST API.

    Usage:
        async with AutotaskClient(config) as client:
            result = await client.get("Tickets/entityInformation")
    """

    def __init__(self, config: AutotaskConfig) -> None:
        self._config = config
        self._http: httpx.AsyncClient | None = None
        self._base_url: str | None = None
        self._rate_limiter = RateLimiter()
        self._semaphore = asyncio.Semaphore(3)  # Autotask: max 3 concurrent threads per endpoint

        if config.api_url:
            self._base_url = f"{config.api_url.rstrip('/')}/atservicesrest/v1.0"

    @property
    def base_url(self) -> str:
        if self._base_url is None:
            raise RuntimeError("Client not initialized. Use 'async with' or call connect().")
        return self._base_url

    async def __aenter__(self) -> AutotaskClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        """Initialize HTTP client and discover zone if needed."""
        self._http = httpx.AsyncClient(
            headers=self._config.auth_headers(),
            timeout=httpx.Timeout(30.0),
        )

        if self._base_url is None:
            await self._discover_zone()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _discover_zone(self) -> None:
        """Discover the correct zone URL for this tenant.

        Autotask routes tenants to different datacenters. The zone URL
        must be discovered at runtime — it cannot be hardcoded.
        Caches result to ~/.cache/autotask/zone.json to avoid 1-2s
        penalty on every CLI invocation.
        """
        # Check cache first
        cached = self._load_zone_cache()
        if cached:
            self._base_url = cached
            return

        assert self._http is not None
        url = f"{ZONE_DISCOVERY_URL}?user={quote(self._config.username)}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        data = resp.json()
        zone_url = data["url"].rstrip("/")
        self._base_url = zone_url

        # Cache for next time
        self._save_zone_cache(zone_url)

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make an authenticated GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> dict[str, Any]:
        """Make an authenticated POST request."""
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: Any = None) -> dict[str, Any]:
        """Make an authenticated PATCH request (partial update, safe)."""
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> dict[str, Any]:
        """Make an authenticated DELETE request."""
        return await self._request("DELETE", path)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with error handling, retry, and concurrency control."""
        if self._http is None:
            raise RuntimeError("Client not initialized. Use 'async with' or call connect().")

        await self._rate_limiter.wait_if_needed()

        async with self._semaphore:  # Max 3 concurrent requests
            url = f"{self.base_url}/{path.lstrip('/')}"
            resp = await self._http.request(method, url, params=params, json=json)

        # Update rate limiter from response headers (if present)
        self._update_rate_limit_from_response(resp)

        if resp.status_code == 404:
            raise AutotaskNotFoundError(f"Not found: {path}")

        if resp.status_code == 401 or resp.status_code == 429:
            if resp.status_code == 401:
                raise AutotaskAuthError(f"Authentication failed (401): {resp.text}")
            raise AutotaskRateLimitError(
                "Rate limit exceeded. 10k requests/hour shared across all integrations."
            )

        if resp.status_code >= 400:
            body = resp.text
            # Autotask also returns 500 for invalid credentials
            if resp.status_code == 500 and _AUTH_ERROR_PATTERNS.search(body):
                raise AutotaskAuthError(f"Authentication failed: {body}")
            raise AutotaskAPIError(
                f"API error {resp.status_code}: {body}",
                status_code=resp.status_code,
                response_body=body,
            )

        return resp.json()  # type: ignore[no-any-return]

    def _update_rate_limit_from_response(self, resp: httpx.Response) -> None:
        """Parse rate limit info from response headers and update the limiter."""
        # Autotask includes threshold info in response headers
        current = resp.headers.get("X-RateLimit-Current")
        threshold = resp.headers.get("X-RateLimit-Limit")
        if current and threshold:
            self._rate_limiter.update(int(current), int(threshold))
```

**Step 4: Run tests**

```bash
pytest tests/test_client.py -v
```
Expected: ALL PASS

**Step 5: Run full test suite + lint**

```bash
pytest -v && ruff check src/ tests/
```

**Step 6: Commit**

```bash
git add src/autotask/client.py tests/test_client.py
git commit -m "feat: core HTTP client with zone discovery and error handling"
```

---

**Phase 1 CHECKPOINT** - Commit, /done, restart

At this point we have:
- Working project scaffold with dev tooling
- Config management (env vars, base64 secret, explicit params)
- Exception hierarchy
- Async HTTP client with zone discovery, auth headers, error handling
- Full test coverage for all of the above

---

## Phase 2: Rate Limiting + Pagination + Query Builder (Session 2)

Goal: Add rate limit awareness, automatic pagination, and the query filter DSL.

### Task 4: Rate Limit Tracking [COMPLETE]

**Files:**
- Create: `src/autotask/rate_limiter.py`
- Create: `tests/test_rate_limiter.py`
- Modify: `src/autotask/client.py` (integrate rate limiter)

**Step 1: Write failing tests**

```python
# tests/test_rate_limiter.py
"""Tests for rate limit tracking and throttling."""

import asyncio
import time
import pytest

from autotask.rate_limiter import RateLimiter


async def test_rate_limiter_no_delay_when_fresh() -> None:
    """No delay when rate limiter has no data."""
    rl = RateLimiter()
    delay = rl.get_delay()
    assert delay == 0.0


async def test_rate_limiter_delay_at_50_percent() -> None:
    """0.5s delay when usage hits 50%."""
    rl = RateLimiter()
    rl.update(current_count=5000, threshold=10000)
    delay = rl.get_delay()
    assert delay == pytest.approx(0.5)


async def test_rate_limiter_delay_at_75_percent() -> None:
    """1.0s delay when usage hits 75%."""
    rl = RateLimiter()
    rl.update(current_count=7500, threshold=10000)
    delay = rl.get_delay()
    assert delay == pytest.approx(1.0)


async def test_rate_limiter_no_delay_below_50_percent() -> None:
    """No delay when usage is below 50%."""
    rl = RateLimiter()
    rl.update(current_count=4000, threshold=10000)
    delay = rl.get_delay()
    assert delay == 0.0
```

**Step 2: Run tests — expect FAIL**

**Step 3: Write rate limiter implementation**

```python
# src/autotask/rate_limiter.py
"""Rate limit tracking for Autotask API.

Autotask enforces 10k requests/hour shared across ALL integrations
on the account. Progressive throttling:
- 50% usage (5000 req) = 0.5s delay between requests
- 75% usage (7500 req) = 1.0s delay between requests
"""

from __future__ import annotations

import asyncio


class RateLimiter:
    """Tracks API rate limit usage and applies progressive delays."""

    def __init__(self) -> None:
        self._current_count: int = 0
        self._threshold: int = 10000

    def update(self, current_count: int, threshold: int) -> None:
        """Update rate limit state from API response headers or ThresholdInformation."""
        self._current_count = current_count
        self._threshold = threshold

    def get_delay(self) -> float:
        """Calculate delay based on current usage percentage."""
        if self._threshold == 0:
            return 0.0

        usage_pct = self._current_count / self._threshold

        if usage_pct >= 0.75:
            return 1.0
        elif usage_pct >= 0.50:
            return 0.5
        return 0.0

    async def wait_if_needed(self) -> None:
        """Sleep if rate limiting requires a delay."""
        delay = self.get_delay()
        if delay > 0:
            await asyncio.sleep(delay)
```

**Step 4: Run tests — expect PASS**

**Step 5: Integrate rate limiter into client.py**

Add to `AutotaskClient.__init__`:
```python
self._rate_limiter = RateLimiter()
```

Add to `AutotaskClient._request` before making the request:
```python
await self._rate_limiter.wait_if_needed()
```

**Step 6: Commit**

```bash
git add src/autotask/rate_limiter.py tests/test_rate_limiter.py src/autotask/client.py
git commit -m "feat: rate limit tracking with progressive throttling"
```

---

### Task 5: Pagination [COMPLETE]

**Files:**
- Modify: `src/autotask/client.py` (add query_all method)
- Modify: `tests/test_client.py` (add pagination tests)

**Step 1: Write failing tests for pagination**

```python
# Add to tests/test_client.py

async def test_query_all_single_page(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """query_all returns items when results fit in one page."""
    httpx_mock.add_response(
        json={"items": [{"id": 1}, {"id": 2}]},
    )

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all("Tickets", filters=[{"field": "status", "op": "eq", "value": 1}])
        assert len(items) == 2


async def test_query_all_paginates(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """query_all auto-paginates when 500 records returned (max page size)."""
    # First page: 500 records (max, triggers next page)
    page1 = [{"id": i} for i in range(1, 501)]
    # Second page: 50 records (under 500, stops)
    page2 = [{"id": i} for i in range(501, 551)]

    httpx_mock.add_response(json={"items": page1})
    httpx_mock.add_response(json={"items": page2})

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all("Tickets", filters=[{"field": "status", "op": "eq", "value": 1}])
        assert len(items) == 550


async def test_query_all_empty(httpx_mock: HTTPXMock, config_with_url: AutotaskConfig) -> None:
    """query_all returns empty list when no results."""
    httpx_mock.add_response(json={"items": []})

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all("Tickets", filters=[])
        assert items == []
```

**Step 2: Run tests — expect FAIL**

**Step 3: Add query_all to client.py**

```python
# Add to AutotaskClient class

MAX_PAGE_SIZE = 500

async def query_all(
    self,
    entity: str,
    filters: list[dict[str, Any]],
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    """Query an entity with automatic pagination.

    Autotask returns max 500 records per query. This method automatically
    paginates by adding an 'id > last_id' filter until all records are fetched.

    Args:
        entity: Entity type name (e.g., "Tickets", "Companies")
        filters: List of filter criteria dicts
        max_records: Optional cap on total records to fetch

    Returns:
        All matching records across all pages.
    """
    all_items: list[dict[str, Any]] = []

    while True:
        body = {"filter": filters}
        result = await self.post(f"{entity}/query", json=body)
        items = result.get("items", [])

        if not items:
            break

        all_items.extend(items)

        if max_records and len(all_items) >= max_records:
            all_items = all_items[:max_records]
            break

        # If we got fewer than 500, we've reached the last page
        if len(items) < MAX_PAGE_SIZE:
            break

        # Paginate: add id > last_id filter
        last_id = items[-1]["id"]
        # Replace any existing id > filter or append
        pagination_filter = {"field": "id", "op": "gt", "value": last_id}
        filters = [f for f in filters if f.get("field") != "id" or f.get("op") != "gt"]
        filters.append(pagination_filter)

    return all_items
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/autotask/client.py tests/test_client.py
git commit -m "feat: automatic pagination for query results"
```

---

### Task 6: Query Filter Builder [COMPLETE]

**Files:**
- Create: `src/autotask/query.py`
- Create: `tests/test_query.py`

**Step 1: Write failing tests**

```python
# tests/test_query.py
"""Tests for query filter builder DSL."""

from autotask.query import Q


def test_simple_eq() -> None:
    """Q builds an equality filter."""
    f = Q(status=1)
    assert f.to_filter() == [{"field": "status", "op": "eq", "value": 1}]


def test_operator_suffix() -> None:
    """Q supports operator suffixes like __gt, __contains."""
    f = Q(id__gt=100)
    assert f.to_filter() == [{"field": "id", "op": "gt", "value": 100}]

    f = Q(title__contains="server")
    assert f.to_filter() == [{"field": "title", "op": "contains", "value": "server"}]


def test_multiple_filters_and() -> None:
    """Multiple kwargs produce AND filters."""
    f = Q(status=1, priority=4)
    filters = f.to_filter()
    assert len(filters) == 2
    fields = {f["field"] for f in filters}
    assert fields == {"status", "priority"}


def test_in_operator() -> None:
    """Q supports __in for list values."""
    f = Q(status__in=[1, 5, 8])
    assert f.to_filter() == [{"field": "status", "op": "in", "value": [1, 5, 8]}]


def test_udf_filter() -> None:
    """Q supports UDF filters with udf=True."""
    f = Q.udf(my_custom_field="value")
    filters = f.to_filter()
    assert filters[0]["udf"] is True


def test_combine_with_and() -> None:
    """Q objects can be combined with &."""
    f = Q(status=1) & Q(priority=4)
    filters = f.to_filter()
    assert len(filters) == 2


def test_raw_filter() -> None:
    """Q.raw passes through a pre-built filter dict."""
    raw = {"field": "status", "op": "eq", "value": 1}
    f = Q.raw(raw)
    assert f.to_filter() == [raw]
```

**Step 2: Run tests — expect FAIL**

**Step 3: Write query builder**

```python
# src/autotask/query.py
"""Query filter builder for Autotask API.

Provides a Django-like Q object for building filter expressions:
    Q(status=1)                    -> {"field": "status", "op": "eq", "value": 1}
    Q(id__gt=100)                  -> {"field": "id", "op": "gt", "value": 100}
    Q(title__contains="server")    -> {"field": "title", "op": "contains", "value": "server"}
    Q(status__in=[1, 5, 8])        -> {"field": "status", "op": "in", "value": [1, 5, 8]}

Supported operators: eq, noteq, gt, gte, lt, lte, beginsWith, endsWith,
contains, exist, notExist, in, notIn
"""

from __future__ import annotations

from typing import Any

VALID_OPS = frozenset({
    "eq", "noteq", "gt", "gte", "lt", "lte",
    "beginsWith", "endsWith", "contains",
    "exist", "notExist", "in", "notIn",
})

# Map Python-style suffixes to Autotask operators
_OP_ALIASES: dict[str, str] = {
    "ne": "noteq",
    "not_eq": "noteq",
    "begins_with": "beginsWith",
    "ends_with": "endsWith",
    "not_exist": "notExist",
    "not_in": "notIn",
}


class Q:
    """Query filter builder with Django-like syntax."""

    def __init__(self, **kwargs: Any) -> None:
        self._filters: list[dict[str, Any]] = []
        for key, value in kwargs.items():
            field, op = self._parse_key(key)
            self._filters.append({"field": field, "op": op, "value": value})

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        """Parse 'field__op' into (field, op). Default op is 'eq'."""
        if "__" in key:
            field, op_raw = key.rsplit("__", 1)
            op = _OP_ALIASES.get(op_raw, op_raw)
            if op not in VALID_OPS:
                raise ValueError(f"Unknown operator: {op_raw} (resolved to {op})")
            return field, op
        return key, "eq"

    @classmethod
    def udf(cls, **kwargs: Any) -> Q:
        """Create a UDF (User Defined Field) filter.

        Only ONE UDF filter is allowed per query (Autotask limitation).
        """
        instance = cls(**kwargs)
        for f in instance._filters:
            f["udf"] = True
        return instance

    @classmethod
    def raw(cls, filter_dict: dict[str, Any]) -> Q:
        """Create a Q from a raw filter dict."""
        instance = cls()
        instance._filters = [filter_dict]
        return instance

    def __and__(self, other: Q) -> Q:
        """Combine two Q objects with AND (all filters in one list).

        Raises ValueError if combining would produce >1 UDF filter
        (Autotask allows only ONE UDF filter per query).
        """
        combined = Q()
        combined._filters = self._filters + other._filters
        udf_count = sum(1 for f in combined._filters if f.get("udf"))
        if udf_count > 1:
            raise ValueError("Autotask allows only ONE UDF filter per query")
        return combined

    def to_filter(self) -> list[dict[str, Any]]:
        """Convert to the Autotask API filter format."""
        return list(self._filters)
```

**Step 4: Run tests — expect PASS**

**Step 5: Run full suite + lint**

```bash
pytest -v && ruff check src/ tests/
```

**Step 6: Commit**

```bash
git add src/autotask/query.py tests/test_query.py
git commit -m "feat: query filter builder with Django-like Q syntax"
```

---

**Phase 2 CHECKPOINT** - Commit, /done, restart

At this point the core engine is complete:
- HTTP client with zone discovery
- Rate limiting with progressive throttling
- Automatic pagination
- Query builder DSL

---

## Phase 3: Entity Models + Generic Entity Access (Session 3)

Goal: Pydantic models for daily-driver entities, generic entity access for all 211 types, and entity metadata introspection.

### Task 7: Entity Metadata Introspection

**Files:**
- Create: `src/autotask/metadata.py`
- Create: `tests/test_metadata.py`

This module fetches entity capabilities and field definitions from the API's self-describing endpoints:
- `GET /{Entity}/entityInformation` — canCreate, canDelete, canQuery, canUpdate
- `GET /{Entity}/entityInformation/fields` — field types, required, picklists
- `GET /{Entity}/entityInformation/userDefinedFields` — UDF definitions

```python
# src/autotask/metadata.py
"""Entity metadata introspection.

Autotask's API is self-describing. These endpoints tell us what operations
are supported, what fields exist, which are required, and picklist values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autotask.client import AutotaskClient


@dataclass
class FieldInfo:
    """Metadata about a single entity field."""
    name: str
    data_type: str
    is_required: bool
    is_read_only: bool
    is_picklist: bool
    picklist_values: list[dict[str, Any]] = field(default_factory=list)
    max_length: int | None = None


@dataclass
class EntityInfo:
    """Metadata about an entity type's capabilities and fields."""
    name: str
    can_create: bool
    can_delete: bool
    can_query: bool
    can_update: bool
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    user_defined_fields: dict[str, FieldInfo] = field(default_factory=dict)


async def get_entity_info(client: AutotaskClient, entity: str) -> EntityInfo:
    """Fetch full entity metadata including capabilities and field definitions."""
    # Fetch capabilities
    info_resp = await client.get(f"{entity}/entityInformation")
    info = info_resp.get("item", info_resp)

    entity_info = EntityInfo(
        name=entity,
        can_create=info.get("canCreate", False),
        can_delete=info.get("canDelete", False),
        can_query=info.get("canQuery", False),
        can_update=info.get("canUpdate", False),
    )

    # Fetch field definitions
    fields_resp = await client.get(f"{entity}/entityInformation/fields")
    for f_data in fields_resp.get("fields", []):
        fi = FieldInfo(
            name=f_data["name"],
            data_type=f_data.get("dataType", "string"),
            is_required=f_data.get("isRequired", False),
            is_read_only=f_data.get("isReadOnly", False),
            is_picklist=f_data.get("isPickList", False),
            picklist_values=f_data.get("picklistValues", []),
            max_length=f_data.get("maxLength"),
        )
        entity_info.fields[fi.name] = fi

    # Fetch UDFs (may 404 if entity has none)
    try:
        udf_resp = await client.get(f"{entity}/entityInformation/userDefinedFields")
        for u_data in udf_resp.get("fields", []):
            fi = FieldInfo(
                name=u_data["name"],
                data_type=u_data.get("dataType", "string"),
                is_required=u_data.get("isRequired", False),
                is_read_only=u_data.get("isReadOnly", False),
                is_picklist=u_data.get("isPickList", False),
                picklist_values=u_data.get("picklistValues", []),
                max_length=u_data.get("maxLength"),
            )
            entity_info.user_defined_fields[fi.name] = fi
    except Exception:
        pass  # Entity has no UDFs

    return entity_info
```

Tests should mock the three endpoints and verify correct parsing.

**Commit message:** `feat: entity metadata introspection from API self-describing endpoints`

---

### Task 8: Generic Entity Manager

**Files:**
- Create: `src/autotask/entity.py`
- Create: `tests/test_entity.py`

Provides CRUD operations for any of the 211 entity types:
- `entity.get(id)` — GET /{Entity}/{id}
- `entity.query(filters)` — POST /{Entity}/query
- `entity.create(data)` — POST /{Entity}
- `entity.update(id, data)` — PATCH /{Entity} (ALWAYS patch, never PUT)
- `entity.delete(id)` — DELETE /{Entity}/{id}
- `entity.count(filters)` — query with count
- Parent-child access: `entity.child("Notes").query(parent_id, filters)`

```python
# src/autotask/entity.py  (key interface, full impl in the file)

class EntityManager:
    """Generic CRUD manager for any Autotask entity type."""

    def __init__(self, client: AutotaskClient, entity_type: str) -> None: ...
    async def get(self, entity_id: int) -> dict[str, Any]: ...
    async def query(self, *q: Q, **kwargs: Any) -> list[dict[str, Any]]: ...
    async def create(self, data: dict[str, Any]) -> dict[str, Any]: ...
    async def update(self, entity_id: int, data: dict[str, Any]) -> dict[str, Any]: ...
    async def delete(self, entity_id: int) -> None: ...
    def child(self, child_entity: str) -> ChildEntityManager: ...
```

**Commit message:** `feat: generic entity manager with CRUD and parent-child access`

---

### Task 9: Daily-Driver Pydantic Models

**Files:**
- Create: `src/autotask/models/__init__.py`
- Create: `src/autotask/models/ticket.py`
- Create: `src/autotask/models/company.py`
- Create: `src/autotask/models/project.py`
- Create: `src/autotask/models/task.py`
- Create: `src/autotask/models/resource.py`
- Create: `src/autotask/models/time_entry.py`
- Create: `tests/test_models.py`

Each model includes:
- Pydantic model with field types matching API
- Picklist enums (Status, Priority, Queue) from your existing mappings
- Convenience classmethods: `Ticket.my_open(client, resource_id)`, `Company.by_name(client, name)`
- Serialization to/from API format

Example Ticket model with your exact picklist mappings:

```python
# src/autotask/models/ticket.py
from enum import IntEnum
from pydantic import BaseModel

class TicketStatus(IntEnum):
    NEW = 1
    COMPLETE = 5
    WAITING_CUSTOMER = 7
    IN_PROGRESS = 8
    WAITING_MATERIALS = 9
    DISPATCHED = 10
    WAITING_VENDOR = 12
    ON_HOLD = 17
    CUSTOMER_NOTE_ADDED = 19
    RMM_RESOLVED = 20
    REFERRED_TO_LEC = 21
    DUPLICATE = 22
    CANCELED = 23
    ESCALATE_TO_BILLING = 25
    SCHEDULED = 26
    # ... etc from brainstorm doc

class TicketPriority(IntEnum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    CRITICAL = 4

class Ticket(BaseModel):
    id: int
    ticket_number: str | None = None
    title: str | None = None
    status: TicketStatus | int | None = None
    priority: TicketPriority | int | None = None
    queue_id: int | None = None
    company_id: int | None = None
    # ... remaining fields
```

**Commit message:** `feat: pydantic models for daily-driver entities with picklist enums`

---

**Phase 3 CHECKPOINT** - Commit, /done, restart

At this point:
- Entity metadata introspection works
- Generic CRUD for any entity type
- Typed Pydantic models for the 10 most-used entities
- Picklist enums from your real tenant data

---

## Phase 4: Typed Entity Services + Library API (Session 4)

Goal: High-level typed services that combine models + entity manager, and a clean public API.

### Task 10: Typed Entity Services

**Files:**
- Create: `src/autotask/services/__init__.py`
- Create: `src/autotask/services/tickets.py`
- Create: `src/autotask/services/companies.py`
- Create: `src/autotask/services/projects.py`
- Create: `tests/test_services.py`

These provide the "smart" layer — `tickets.my_open()`, `tickets.by_queue()`, `companies.by_name()`, etc. They return typed Pydantic models, handle secondary resource deduplication (ported from your 1ife-os pattern), and provide LOB-aware filtering (ported from your pm pattern).

### Task 11: Public API Surface

**Files:**
- Modify: `src/autotask/__init__.py`
- Create: `tests/test_public_api.py`

Clean imports:
```python
from autotask import AutotaskClient, AutotaskConfig, Q
from autotask.models import Ticket, Company, Project, Task
from autotask.services import TicketService, CompanyService
```

### Task 12: Caching Layer

**Files:**
- Create: `src/autotask/cache.py`
- Create: `tests/test_cache.py`

In-memory cache for lookup tables (companies, resources, queues) that rarely change. Ported from both pm (multi-level) and 1ife-os (simple Map) patterns, hitting the sweet spot:
- TTL-based (default 5 min for entities, 1 hour for picklists)
- Optional — caching can be disabled
- Thread-safe with asyncio locks

**Commit message:** `feat: typed entity services, public API, and caching layer`

---

**Phase 4 CHECKPOINT** - Commit, /done, restart

---

## Phase 5: CLI Wrapper (Session 5)

Goal: Thin Click CLI over the library for quick lookups and operations.

### Task 13: CLI Foundation

**Files:**
- Create: `src/autotask/cli.py`
- Create: `tests/test_cli.py`

```bash
# Daily-driver commands
autotask tickets list --status open --mine
autotask tickets get 12345
autotask tickets create --title "New ticket" --company 264 --priority medium
autotask companies search "Acme"
autotask projects list --active
autotask time log --ticket 12345 --hours 1.5 --summary "Fixed the thing"

# Generic fallback for any entity
autotask entity query ConfigurationItems --filter "status=eq=1"
autotask entity get Contacts 5678
autotask entity info Tickets  # show entity metadata

# Utility
autotask rate-limit  # check current usage
autotask whoami  # show authenticated user
```

### Task 14: CLI Output Formatting

**Files:**
- Modify: `src/autotask/cli.py`

Support `--json` flag (raw JSON output for piping) and default table format for human reading.

**Commit message:** `feat: Click CLI with daily-driver commands and generic entity access`

---

**Phase 5 CHECKPOINT** - Commit, /done, restart

---

## Phase 6: Docs + Integration Tests + Polish (Session 6)

Goal: Knowledge base docs for Claude, integration tests with real API, and final polish.

### Task 15: Claude Knowledge Base (docs/)

**Files:**
- Create: `docs/api-reference.md` — Entity types, fields, operations, gotchas
- Create: `docs/query-syntax.md` — Filter operators, pagination, UDF queries
- Create: `docs/rate-limits.md` — Thresholds, progressive throttling, best practices
- Create: `docs/picklists.md` — All your tenant-specific picklist mappings
- Create: `docs/webhooks.md` — Supported entities, limitations, latency
- Create: `docs/migration-guide.md` — How to replace pm/1ife-os inline code with library imports

This is the key deliverable that stops Claude from relearning. These docs get loaded as context whenever Claude works on any project using Autotask.

### Task 16: Integration Tests

**Files:**
- Create: `tests/integration/test_live_api.py`
- Create: `tests/integration/conftest.py`

Marked with `@pytest.mark.integration` — skipped in CI, run manually with real creds from 1Password:

```bash
autotask whoami  # verify creds work
pytest tests/integration/ -v -m integration
```

Tests: zone discovery, entity info fetch, ticket query, company lookup, rate limit check.

### Task 17: Final Polish

- Update `__init__.py` exports
- Verify `pip install -e .` works cleanly
- Verify `autotask --help` works
- Run full `pytest && ruff check && mypy src/`
- Tag v0.1.0

**Commit message:** `docs: Claude knowledge base, integration tests, and v0.1.0 polish`

---

**Phase 6 CHECKPOINT** - Commit, tag v0.1.0, /done

---

## Phase 7: Migration Recommendations (Session 7, Optional)

Goal: Post-build deliverables from the brainstorm.

### Task 18: Migration Plan for pm and 1ife-os

Analyze both codebases and produce concrete PRs or migration docs:
- Which imports to replace
- Which inline logic to delete
- Which cached data to pull from the library instead

### Task 19: New Use Case Ideas

Based on the full API surface (211 entity types), suggest automations and dashboards the user hasn't built yet but could with the library.

---

## Questions (Resolved)

1. **1Password secret names:** Look up during Phase 6 integration tests — `op item list --vault ClaudeAgents --tags autotask`
2. ~~**LOB filtering:**~~ **RESOLVED** — Configurable via `AutotaskConfig.lob_mappings` dict. Not hardcoded.
3. ~~**Template company IDs:**~~ **RESOLVED** — Configurable via `AutotaskConfig.template_company_ids` list. Not hardcoded.
4. ~~**Async-only or sync wrapper?**~~ **RESOLVED** — Async-only. Consumers use `asyncio.run()`.
5. ~~**GitHub repo:**~~ **RESOLVED** — Local-only until Phase 6 complete, then create repo.

## Risks

1. **API quirks not captured in brainstorm** — The Autotask API has undocumented behaviors. Integration tests may reveal surprises not in the existing TypeScript code.
2. **pytest-httpx version compatibility** — Async mock libraries can be finicky. Pin versions carefully.
3. **Picklist drift** — Picklist IDs are tenant-specific and can change. The enum approach works for YOUR tenant but isn't portable. The metadata introspection fallback handles this.
4. **Rate limit sharing** — The 10k/hr limit is shared with your existing MCP server and any other integrations. Heavy library use during testing could throttle production tools. Keep integration test volume conservative.
5. **Secret leakage in error logs** — Ensure `AutotaskAPIError` and httpx logging don't serialize auth headers (`UserName`, `Secret`) when raising exceptions. Sanitize before logging.
6. **UDF missing from responses** — Autotask omits UDF fields when no values are set. All UDF fields in Pydantic models MUST default to `None` to avoid `ValidationError`.

## Gemini Review Applied

Changes incorporated from Gemini plan review (2026-03-17):
- Added `asyncio.Semaphore(3)` for per-endpoint concurrency control
- Added tenacity `@retry` on `_request` for transient failures
- Added response header parsing to feed `RateLimiter.update()`
- Added UDF count validation in `Q.__and__`
- Added `lob_mappings` and `template_company_ids` to `AutotaskConfig`
- Added zone URL caching to `~/.cache/autotask/zone.json`
- Handle both 401 AND 500 for auth errors (docs say 401, real API sometimes returns 500)
- Added `query/count` endpoint support to entity manager
