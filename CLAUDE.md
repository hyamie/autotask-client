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
