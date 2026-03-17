# autotask-client

Async Python client for the [Autotask REST API](https://ww5.autotask.net/help/DeveloperHelp/Content/APIs/REST/REST_API_Home.htm). Handles zone discovery, authentication, rate limiting, pagination, and all 211 entity types out of the box.

## Install

```bash
pip install autotask-client
```

## Quick Start

```python
import asyncio
from autotask import AutotaskClient, AutotaskConfig, EntityManager
from autotask.models import Ticket, Company
from autotask.query import Q

async def main():
    config = AutotaskConfig(
        username="user@example.com",
        secret="your-api-secret",
        integration_code="your-integration-code",
    )
    async with AutotaskClient(config) as client:
        em = EntityManager(client)

        # Query tickets by status
        tickets = await em.query(Ticket, Q(status=8))

        # Get a single company
        company = await em.get(Company, 12345)

        # Create a ticket
        ticket = Ticket(
            title="Server down",
            companyID=12345,
            status=1,
            priority=1,
        )
        created = await em.create(ticket)

        # Update with PATCH (only specified fields change)
        updated = await em.update(Ticket(id=created.id, status=5))

        # Query any of the 211 entity types by name
        items = await em.query("ConfigurationItems", Q(isActive=True))

asyncio.run(main())
```

## Configuration

### Environment Variables

```bash
export AUTOTASK_USERNAME="user@example.com"
export AUTOTASK_SECRET="your-secret"
export AUTOTASK_INTEGRATION_CODE="your-code"

# Optional
export AUTOTASK_API_URL="https://webservicesX.autotask.net/atservicesrest"
export AUTOTASK_RESOURCE_ID="12345"
```

```python
config = AutotaskConfig.from_env()
```

`AUTOTASK_SECRET_B64` is also supported for platforms that mangle special characters (base64-encoded secret).

If `AUTOTASK_API_URL` is not set, the client automatically discovers your zone via the Autotask zone information endpoint and caches it to `~/.cache/autotask/zone.json`.

## Query DSL

Django-inspired filter syntax:

```python
from autotask.query import Q

Q(status=1)                        # eq (default)
Q(id__gt=100)                      # greater than
Q(title__contains="server")        # contains
Q(status__in=[1, 5, 8])            # in list
Q(priority__gte=2, status__noteq=5)  # multiple filters (AND)

# UDF (User Defined Field) filters — one per query (API limitation)
Q.udf(myCustomField__contains="value")

# Combine with &
filters = Q(status=1) & Q(companyID=123)
```

Supported operators: `eq`, `noteq`, `gt`, `gte`, `lt`, `lte`, `beginsWith`, `endsWith`, `contains`, `exist`, `notExist`, `in`, `notIn`

## Entity Models

Hand-crafted Pydantic models for common entities with typed fields and validation:

| Model | API Entity |
|-------|------------|
| `Ticket` | Tickets |
| `Company` | Companies |
| `Project` | Projects |
| `Task` | Tasks (child of Project) |
| `Resource` | Resources |
| `TimeEntry` | TimeEntries |
| `TicketNote` | TicketNotes (child of Ticket) |
| `ProjectNote` | ProjectNotes (child of Project) |
| `TaskNote` | TaskNotes (child of Task) |

All models use `extra="allow"` to preserve unmodeled fields during round-trips.

For entity types without a hand-crafted model, pass the entity name as a string — the manager returns raw dicts:

```python
items = await em.query("Contacts", Q(isActive=True))
```

## CLI

```bash
# List tickets
autotask tickets list --status 8 --limit 10

# Get a ticket
autotask tickets get 12345

# Create a ticket
autotask tickets create --title "Fix printer" --company-id 123

# Update a ticket
autotask tickets update 12345 --status 5 --priority 1

# Query any entity type
autotask query ConfigurationItems isActive=true --limit 20

# Inspect entity metadata
autotask info Tickets
autotask fields Tickets

# Check config
autotask config
```

Output is JSON by default (designed for scripting/AI consumption). Use `--table` for human-readable output:

```bash
autotask --table tickets list --limit 5
```

## API Behavior

Things this library handles so you don't have to:

- **Zone discovery** — Autotask routes tenants to different datacenters. The client discovers and caches the correct URL automatically.
- **Auth via headers** — `UserName`, `Secret`, `ApiIntegrationCode` on every request.
- **Rate limiting** — Progressive throttling at 50% and 75% of the 10k req/hour shared limit. Reads usage from response headers.
- **Pagination** — `query_all()` automatically paginates using `id > last_id` (max 500 per page).
- **Retry** — Transient failures (connection errors, timeouts) retry with exponential backoff (3 attempts).
- **Concurrency** — Semaphore limits to 3 concurrent requests per endpoint.
- **Error mapping** — 401 and 500-with-auth-pattern both raise `AutotaskAuthError`. 404 raises `AutotaskNotFoundError`. The API returns `{item: null}` instead of 404 for missing entities — this is handled correctly.

## Requirements

- Python 3.12+
- httpx, pydantic, click, tenacity

## License

MIT
