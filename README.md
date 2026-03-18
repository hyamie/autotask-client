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

Output is JSON by default (designed for scripting/AI consumption). Use `--table` for human-readable output.

### Entity Commands

Full CRUD for the core entity types:

```bash
# Tickets
autotask tickets list --status 8 --limit 10
autotask tickets get 12345
autotask tickets create --title "Fix printer" --company-id 123
autotask tickets update 12345 --status 5 --priority 1
autotask tickets delete 12345

# Companies
autotask companies list --limit 10
autotask companies get 12345
autotask companies create --name "Acme Corp"
autotask companies update 12345 --name "Acme Inc"

# Projects
autotask projects list --limit 10
autotask projects get 12345

# Tasks (queried via projectID filter, not a child entity)
autotask tasks list --project-id 12345
autotask tasks get 67890
autotask tasks create --project-id 12345 --title "Migrate database"
autotask tasks update 67890 --status 5

# Time entries
autotask time-entries list --limit 10
autotask time-entries create --ticket-id 12345 --hours 1.5
autotask time-entries update 67890 --hours 2.0

# Resources (read-only)
autotask resources list --limit 10
autotask resources get 12345
```

### Notes (Child Entities)

Notes are children of their parent entity — the parent ID is required:

```bash
# Ticket notes
autotask ticket-notes list 12345          # notes on ticket 12345
autotask ticket-notes get 12345 67890     # note 67890 on ticket 12345
autotask ticket-notes create 12345 --title "Update" --description "Fixed the issue"

# Project notes
autotask project-notes list 12345
autotask project-notes create 12345 --title "Status" --description "On track"

# Task notes
autotask task-notes list 67890
autotask task-notes create 67890 --title "Progress" --description "50% done"
```

### Generic Commands

Work with any of the 211 Autotask entity types:

```bash
# Query any entity
autotask query ConfigurationItems isActive=true --limit 20
autotask query Contacts firstName=John --limit 10

# Get/create/update/delete by entity type
autotask get Tickets 12345
autotask create Tickets --fields '{"title":"Test","companyID":123,"status":1,"priority":2}'
autotask update Tickets 12345 --fields '{"status":5,"priority":1}'
autotask delete Tickets 12345

# Child entities use --parent-id
autotask get TicketNotes 67890 --parent-id 12345
```

### Metadata & Utilities

```bash
autotask info Tickets           # Entity capabilities (canCreate, canQuery, etc.)
autotask fields Tickets         # Field definitions, types, required flags
autotask picklist Tickets status  # Resolve picklist IDs to labels
autotask whoami                 # Authenticated user's resource record
autotask config                 # Show current configuration (no secrets)

# Table output
autotask --table tickets list --limit 5
```

## MCP Server

The package includes an [MCP](https://modelcontextprotocol.io/) server for LLM tool use. Install with the `mcp` extra:

```bash
pip install autotask-client[mcp]
```

### Tools

| Tool | Description |
|------|-------------|
| `autotask_query` | Query any entity with filters and pagination |
| `autotask_get` | Get a single entity by ID |
| `autotask_create` | Create an entity from field values |
| `autotask_update` | PATCH update (only specified fields change) |
| `autotask_delete` | Delete an entity by ID |
| `autotask_entity_info` | Entity capabilities (canCreate, canQuery, etc.) |
| `autotask_field_info` | Field definitions, types, picklist references |
| `autotask_resolve_picklist` | Resolve picklist field to {id: label} mapping |
| `autotask_whoami` | Authenticated user's resource record |

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "autotask": {
      "command": "autotask-mcp",
      "env": {
        "AUTOTASK_USERNAME": "user@example.com",
        "AUTOTASK_SECRET": "your-api-secret",
        "AUTOTASK_INTEGRATION_CODE": "your-integration-code"
      }
    }
  }
}
```

Or if installed via pipx:

```json
{
  "mcpServers": {
    "autotask": {
      "command": "pipx",
      "args": ["run", "--spec", "autotask-client[mcp]", "autotask-mcp"],
      "env": {
        "AUTOTASK_USERNAME": "user@example.com",
        "AUTOTASK_SECRET": "your-api-secret",
        "AUTOTASK_INTEGRATION_CODE": "your-integration-code"
      }
    }
  }
}
```

### Claude Code Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "autotask": {
      "command": "autotask-mcp",
      "env": {
        "AUTOTASK_USERNAME": "user@example.com",
        "AUTOTASK_SECRET": "your-api-secret",
        "AUTOTASK_INTEGRATION_CODE": "your-integration-code"
      }
    }
  }
}
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
