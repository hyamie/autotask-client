"""Tests for core HTTP client."""

import json

import pytest
from pytest_httpx import HTTPXMock

import autotask.client as client_module
from autotask.client import AutotaskClient
from autotask.config import AutotaskConfig
from autotask.exceptions import AutotaskAPIError, AutotaskAuthError, AutotaskRateLimitError


@pytest.fixture(autouse=True)
def _no_zone_cache(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent zone cache from interfering with tests."""
    monkeypatch.setattr(client_module, "_ZONE_CACHE_PATH", tmp_path / "zone.json")


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


async def test_zone_discovery_skipped_when_url_provided(
    config_with_url: AutotaskConfig,
) -> None:
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


async def test_get_sends_auth_headers(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
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
        result = await client.post(
            "Tickets/query",
            json={"filter": [{"field": "status", "op": "eq", "value": 1}]},
        )
        assert result["items"][0]["title"] == "Test Ticket"


# --- Error Handling ---


async def test_auth_error_on_500_with_auth_message(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
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


async def test_generic_api_error(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """Non-auth errors raise AutotaskAPIError."""
    httpx_mock.add_response(
        status_code=400,
        json={"errors": ["Invalid filter"]},
    )

    async with AutotaskClient(config_with_url) as client:
        with pytest.raises(AutotaskAPIError) as exc_info:
            await client.get("Tickets")
        assert exc_info.value.status_code == 400


async def test_rate_limit_error_carries_autotasks_own_reason(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """A 429 names both limits and passes on Autotask's text, so a caller can tell a
    concurrency refusal from an exhausted hourly pool."""
    httpx_mock.add_response(status_code=429, text="Thread threshold of 3 exceeded")

    async with AutotaskClient(config_with_url) as client:
        with pytest.raises(AutotaskRateLimitError) as exc_info:
            await client.get("Tickets")
    message = str(exc_info.value)
    assert "Thread threshold of 3 exceeded" in message
    assert "3 at a time" in message and "10k/hour" in message


# --- Pagination ---


async def test_query_all_single_page(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """query_all returns items when results fit in one page."""
    httpx_mock.add_response(json={"items": [{"id": 1}, {"id": 2}]})

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all(
            "Tickets", filters=[{"field": "status", "op": "eq", "value": 1}]
        )
        assert len(items) == 2


async def test_query_all_paginates(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """query_all auto-paginates when 500 records returned (max page size)."""
    page1 = [{"id": i} for i in range(1, 501)]
    page2 = [{"id": i} for i in range(501, 551)]

    httpx_mock.add_response(json={"items": page1})
    httpx_mock.add_response(json={"items": page2})

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all(
            "Tickets", filters=[{"field": "status", "op": "eq", "value": 1}]
        )
        assert len(items) == 550


async def test_query_all_empty(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """query_all returns empty list when no results."""
    httpx_mock.add_response(json={"items": []})

    async with AutotaskClient(config_with_url) as client:
        items = await client.query_all("Tickets", filters=[])
        assert items == []


async def test_include_fields_always_asks_for_id(
    httpx_mock: HTTPXMock, config_with_url: AutotaskConfig
) -> None:
    """Pagination reads the last row's id, so a field list without id still gets it."""
    httpx_mock.add_response(json={"items": [{"id": 1, "status": 8}]})

    async with AutotaskClient(config_with_url) as client:
        rows = await client.query_all("Tickets", [], include_fields=["status"])
    assert rows == [{"id": 1, "status": 8}]
    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent["IncludeFields"] == ["id", "status"]
