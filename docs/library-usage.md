# Library Usage Guide

How to use autotask-client in Python code and from the CLI.

## Installation

```bash
pip install -e ".[dev]"   # from repo root
```

## Python Library

### Basic Setup

```python
from autotask.config import AutotaskConfig
from autotask.client import AutotaskClient
from autotask.entities import EntityManager
from autotask.models import Ticket, Company, Resource, Project, TimeEntry
from autotask.query import Q

config = AutotaskConfig.from_env()  # reads AUTOTASK_* env vars

async with AutotaskClient(config) as client:
    em = EntityManager(client)
    # ... use em for all operations
```

### Querying

```python
# Typed query — returns list[Ticket]
tickets = await em.query(Ticket, Q(status=8), max_records=10)

# Multiple filters (AND)
tickets = await em.query(
    Ticket,
    Q(status=8),
    Q(queueID=29975869),
    Q(assignedResourceID=123),
)

# Operator filters
tickets = await em.query(Ticket, Q(id__gt=50000), Q(title__contains="server"))

# UDF filter (only one per query)
tickets = await em.query(Ticket, Q(status=8), Q.udf(MyCustomField="value"))

# Generic entity (returns list[dict])
items = await em.query("ConfigurationItems", Q(isActive=True))

# String entity names auto-resolve to models if registered
tickets = await em.query("Tickets", Q(status=1))  # returns list[Ticket]
```

### Get by ID

```python
ticket = await em.get(Ticket, 12345)

# Child entity needs parent_id
task = await em.get(Task, 456, parent_id=789)  # GET /Projects/789/Tasks/456
```

### Create

```python
ticket = Ticket(
    title="Server down",
    companyID=100,
    status=1,
    priority=4,
    queueID=29975869,
)
created = await em.create(ticket)
print(created.id)  # Auto-assigned ID
```

### Update (PATCH)

```python
ticket = await em.get(Ticket, 12345)
ticket.status = 5  # Complete
ticket.priority = 3  # Low
updated = await em.update(ticket)
```

### Delete

```python
await em.delete(Ticket, 12345)
```

### Entity Metadata

```python
info = await em.entity_info(Ticket)     # canCreate, canQuery, etc.
fields = await em.field_info(Ticket)     # field types, required, picklists
fields = await em.field_info("ConfigurationItems")  # works with strings too
```

### Extra Fields (Round-Tripping)

Models use `extra="allow"`, so unmodeled API fields are preserved:

```python
ticket = await em.get(Ticket, 12345)
# ticket has all API fields, even ones not in the Ticket model
# Modify and save — unmodeled fields pass through unchanged
ticket.status = 5
await em.update(ticket)
```

## CLI

### Configuration

Set environment variables (or use 1Password):
```bash
export AUTOTASK_USERNAME=user@example.com
export AUTOTASK_SECRET=your-secret
export AUTOTASK_INTEGRATION_CODE=YOUR_CODE
export AUTOTASK_API_URL=https://webservices24.autotask.net  # optional, discovered if not set
```

### Commands

```bash
# Tickets
autotask tickets list --status 8 --limit 10
autotask tickets get 12345
autotask tickets create --title "Server down" --company-id 100 --priority 4
autotask tickets update 12345 --status 5

# Companies
autotask companies list --search "Acme"
autotask companies list --all    # include inactive
autotask companies get 100

# Resources
autotask resources list --search "Smith"
autotask resources get 42

# Projects
autotask projects list --company 100
autotask projects get 789

# Time entries
autotask time-entries list --resource 42 --ticket 12345
autotask time-entries get 999

# Generic query (any entity type)
autotask query Tickets status=8 queueID=29975869
autotask query ConfigurationItems isActive=true
autotask query Contacts companyID=100

# Filter operators
autotask query Tickets id__gt=50000 title__contains=server

# Entity metadata
autotask info Tickets
autotask fields Tickets

# Config check
autotask config
```

### Output Format

- Default: JSON (for Claude Code / scripting)
- `--table` flag for human-readable output: `autotask --table tickets list`

### Error Output

Errors are JSON to stderr with structure:
```json
{"error": "auth|not_found|api|validation", "message": "..."}
```
