"""Core HTTP client for Autotask REST API.

Handles authentication, zone discovery, rate limit awareness, and
request/response processing. This is the foundation everything else builds on.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from autotask.config import AutotaskConfig
from autotask.exceptions import (
    AutotaskAPIError,
    AutotaskAuthError,
    AutotaskNotFoundError,
    AutotaskRateLimitError,
)
from autotask.rate_limiter import RateLimiter

ZONE_DISCOVERY_URL = "https://webservices.autotask.net/atservicesrest/v1.0/zoneInformation"
_ZONE_CACHE_PATH = Path.home() / ".cache" / "autotask" / "zone.json"

# Patterns in 500 responses that indicate auth failures
_AUTH_ERROR_PATTERNS = re.compile(
    r"(invalid credentials|authentication|unauthorized|login failed)",
    re.IGNORECASE,
)

# Valid Autotask zone hostnames
_ALLOWED_ZONE_HOSTS = re.compile(r"^webservices\d*\.autotask\.net$")

_MAX_ERROR_BODY_LEN = 500
_MAX_PAGE_SIZE = 500


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
        self._semaphore = asyncio.Semaphore(3)

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
        """
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

        parsed = urlparse(zone_url)
        if parsed.scheme != "https" or not _ALLOWED_ZONE_HOSTS.match(parsed.netloc):
            raise AutotaskAPIError(
                f"Zone discovery returned unexpected URL: {parsed.netloc}",
            )

        self._base_url = zone_url
        self._save_zone_cache(zone_url)

    def _load_zone_cache(self) -> str | None:
        """Load cached zone URL if it exists and matches current username."""
        try:
            data = json.loads(_ZONE_CACHE_PATH.read_text())
            if data.get("username") == self._config.username:
                return data["url"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return None

    def _save_zone_cache(self, url: str) -> None:
        """Cache zone URL to avoid repeated discovery calls."""
        _ZONE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ZONE_CACHE_PATH.write_text(
            json.dumps({"username": self._config.username, "url": url})
        )
        os.chmod(_ZONE_CACHE_PATH, 0o600)

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

    async def query_all(
        self,
        entity: str,
        filters: list[dict[str, Any]],
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query an entity with automatic pagination.

        Autotask returns max 500 records per query. This method automatically
        paginates by adding an 'id > last_id' filter until all records are fetched.
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

            if len(items) < _MAX_PAGE_SIZE:
                break

            last_id = items[-1]["id"]
            pagination_filter = {"field": "id", "op": "gt", "value": last_id}
            filters = [f for f in filters if not (f.get("field") == "id" and f.get("op") == "gt")]
            filters.append(pagination_filter)

        return all_items

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

        async with self._semaphore:
            url = f"{self.base_url}/{path.lstrip('/')}"
            resp = await self._http.request(method, url, params=params, json=json)

        self._update_rate_limit_from_response(resp)

        if resp.status_code == 404:
            raise AutotaskNotFoundError(f"Not found: {path}")

        if resp.status_code == 401:
            raise AutotaskAuthError("Authentication failed (401)")

        if resp.status_code == 429:
            raise AutotaskRateLimitError(
                "Rate limit exceeded. 10k requests/hour shared across all integrations."
            )

        if resp.status_code >= 400:
            body = resp.text
            truncated = body[:_MAX_ERROR_BODY_LEN] if len(body) > _MAX_ERROR_BODY_LEN else body
            if resp.status_code == 500 and _AUTH_ERROR_PATTERNS.search(body):
                raise AutotaskAuthError("Authentication failed (500)")
            raise AutotaskAPIError(
                f"API error {resp.status_code}: {truncated}",
                status_code=resp.status_code,
                response_body=truncated,
            )

        return resp.json()  # type: ignore[no-any-return]

    def _update_rate_limit_from_response(self, resp: httpx.Response) -> None:
        """Parse rate limit info from response headers and update the limiter."""
        current = resp.headers.get("X-RateLimit-Current")
        threshold = resp.headers.get("X-RateLimit-Limit")
        if current and threshold:
            self._rate_limiter.update(int(current), int(threshold))
