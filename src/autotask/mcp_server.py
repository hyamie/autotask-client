"""MCP server for Autotask REST API.

Exposes the autotask-client library as MCP tools for LLM consumption.
Uses FastMCP with stdio transport (default).

Install: pip install autotask-client[mcp]
Run: autotask-mcp
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from fastmcp import FastMCP

from autotask.client import AutotaskClient
from autotask.config import AutotaskConfig
from autotask.entities.manager import EntityManager
from autotask.exceptions import AutotaskError
from autotask.models.base import AutotaskModel, get_model_class
from autotask.query import Q

_SERVER_INSTRUCTIONS = """\
Autotask PSA REST API tools. Important behavioral notes:

- Entity names are PascalCase plural (Tickets, Companies, Resources, Projects, TimeEntries).
- Child entities need parent_id (e.g., TicketNotes under Tickets, ProjectTasks under Projects).
- Filters use field=value with optional __op suffix: status=8, id__gt=100, title__contains=server.
- Supported operators: eq, noteq, gt, gte, lt, lte, beginsWith, endsWith, contains, in, notIn.
- Updates use PATCH (partial) — only specified fields change; unspecified fields are untouched.
- Max 500 records per query page; pagination is automatic.
- Rate limit: 10k requests/hour shared across ALL integrations.
- Picklist fields store integer IDs — use autotask_resolve_picklist to get human-readable labels.
- Invalid credentials return HTTP 500, not 401.
- Empty results from queries may indicate permission issues, not missing data.
"""

_ENTITY_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,60}$")
_MAX_QUERY_LIMIT = 500

mcp = FastMCP(
    name="autotask",
    instructions=_SERVER_INSTRUCTIONS,
    version="0.2.0",
)


def _error(msg: str) -> str:
    return json.dumps({"error": msg})


def _validate_entity(entity: str) -> str | None:
    """Validate entity name. Returns error JSON string if invalid, None if OK."""
    if not _ENTITY_NAME_RE.fullmatch(entity):
        return _error("Invalid entity name. Use PascalCase (e.g., Tickets, Companies).")
    return None


async def _get_manager() -> tuple[AutotaskClient, EntityManager]:
    try:
        config = AutotaskConfig.from_env()
    except ValueError:
        raise AutotaskError("Server misconfigured: missing required credentials")
    client = AutotaskClient(config)
    await client.connect()
    return client, EntityManager(client)


def _resolve_entity(entity: str) -> type[AutotaskModel] | str:
    model = get_model_class(entity)
    return model if model else entity


def _parse_filters(filters: dict[str, Any] | None) -> list[Q]:
    if not filters:
        return []
    return [Q(**{k: v}) for k, v in filters.items()]


def _serialize(data: Any) -> Any:
    if isinstance(data, AutotaskModel):
        return data.model_dump(mode="json", exclude_none=True)
    if isinstance(data, list):
        return [_serialize(item) for item in data]
    if isinstance(data, dict):
        return data
    return data


@mcp.tool
async def autotask_query(
    entity: str,
    filters: dict[str, Any] | None = None,
    limit: int = 50,
    parent_id: int | None = None,
) -> str:
    """Query any Autotask entity with filters.

    Args:
        entity: Entity type name (e.g., Tickets, Companies, Resources, Projects).
        filters: Filter dict with field=value pairs. Use __op suffix for operators
                 (e.g., {"status": 8, "id__gt": 100, "title__contains": "server"}).
        limit: Maximum records to return (default 50, max 500).
        parent_id: Parent entity ID for child entities (e.g., ticket ID for TicketNotes).
    """
    if err := _validate_entity(entity):
        return err
    limit = min(max(limit, 1), _MAX_QUERY_LIMIT)
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        q_filters = _parse_filters(filters)
        results = await em.query(target, *q_filters, parent_id=parent_id, max_records=limit)
        return json.dumps(_serialize(results), indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_get(
    entity: str,
    id: int,
    parent_id: int | None = None,
) -> str:
    """Get a single Autotask entity by ID.

    Args:
        entity: Entity type name (e.g., Tickets, Companies).
        id: The entity ID.
        parent_id: Parent entity ID for child entities.
    """
    if err := _validate_entity(entity):
        return err
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        result = await em.get(target, id, parent_id=parent_id)
        return json.dumps(_serialize(result), indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_create(
    entity: str,
    fields: dict[str, Any],
    parent_id: int | None = None,
) -> str:
    """Create an Autotask entity.

    Args:
        entity: Entity type name (e.g., Tickets, Companies).
        fields: Dict of field values for the new entity.
        parent_id: Parent entity ID for child entities.
    """
    if err := _validate_entity(entity):
        return err
    model_class = get_model_class(entity)
    if model_class is None:
        return _error(f"No model registered for entity: {entity}. Use a known entity type.")
    client, em = await _get_manager()
    try:
        instance = model_class.model_validate(fields)
        result = await em.create(instance, parent_id=parent_id)
        return json.dumps(_serialize(result), indent=2, default=str)
    except ValidationError as e:
        return _error(f"Field validation failed: {e.errors(include_url=False)}")
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_update(
    entity: str,
    id: int,
    fields: dict[str, Any],
    parent_id: int | None = None,
) -> str:
    """Update an Autotask entity (PATCH — only specified fields change).

    Args:
        entity: Entity type name (e.g., Tickets, Companies).
        id: The entity ID to update.
        fields: Dict of fields to update (unspecified fields are untouched).
        parent_id: Parent entity ID for child entities.
    """
    if err := _validate_entity(entity):
        return err
    model_class = get_model_class(entity)
    if model_class is None:
        return _error(f"No model registered for entity: {entity}. Use a known entity type.")
    client, em = await _get_manager()
    try:
        fields["id"] = id
        instance = model_class.model_validate(fields)
        result = await em.update(instance, parent_id=parent_id)
        return json.dumps(_serialize(result), indent=2, default=str)
    except ValidationError as e:
        return _error(f"Field validation failed: {e.errors(include_url=False)}")
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_delete(
    entity: str,
    id: int,
    parent_id: int | None = None,
) -> str:
    """Delete an Autotask entity by ID.

    Args:
        entity: Entity type name.
        id: The entity ID to delete.
        parent_id: Parent entity ID for child entities.
    """
    if err := _validate_entity(entity):
        return err
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        await em.delete(target, id, parent_id=parent_id)
        return json.dumps({"status": "deleted", "entity": entity, "id": id})
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_entity_info(entity: str) -> str:
    """Get entity capabilities (canCreate, canQuery, canUpdate, canDelete, etc.).

    Args:
        entity: Entity type name (e.g., Tickets, Companies).
    """
    if err := _validate_entity(entity):
        return err
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        result = await em.entity_info(target)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_field_info(entity: str) -> str:
    """Get field definitions for an entity (names, types, required, picklist references).

    Args:
        entity: Entity type name (e.g., Tickets, Companies).
    """
    if err := _validate_entity(entity):
        return err
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        result = await em.field_info(target)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_resolve_picklist(entity: str, field: str) -> str:
    """Resolve a picklist field to human-readable {id: label} mapping.

    Args:
        entity: Entity type name (e.g., Tickets).
        field: Field name with picklist values (e.g., status, priority, queueID).
    """
    if err := _validate_entity(entity):
        return err
    client, em = await _get_manager()
    try:
        target = _resolve_entity(entity)
        result = await em.resolve_picklist(target, field)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


@mcp.tool
async def autotask_whoami() -> str:
    """Get the authenticated user's Resource record from Autotask."""
    client, em = await _get_manager()
    try:
        result = await em.whoami()
        return json.dumps(_serialize(result), indent=2, default=str)
    except Exception as e:
        return _error(str(e)) if isinstance(e, AutotaskError) else _error("Internal error")
    finally:
        await client.close()


def main() -> None:
    """Entrypoint for autotask-mcp console script."""
    mcp.run()


if __name__ == "__main__":
    main()
