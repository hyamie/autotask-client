"""CLI wrapper for Autotask REST API client.

Thin Click wrapper over the library. Primary consumer is Claude Code,
so JSON output is the default. Use --table for human-readable output.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import click

from autotask.client import AutotaskClient
from autotask.config import AutotaskConfig
from autotask.entities.manager import EntityManager
from autotask.exceptions import AutotaskAPIError, AutotaskAuthError, AutotaskNotFoundError
from autotask.models import (
    Company,
    Project,
    Resource,
    Ticket,
    TimeEntry,
)
from autotask.models.base import AutotaskModel, get_model_class
from autotask.query import Q


def _run(coro: Any) -> Any:
    """Run an async coroutine from sync Click context."""
    return asyncio.run(coro)


def _output(data: Any, *, as_json: bool = True) -> None:
    """Print output. Models are serialized to dicts first."""
    if isinstance(data, list):
        items = [_to_dict(item) for item in data]
        if as_json:
            click.echo(json.dumps(items, indent=2, default=str))
        else:
            _print_table(items)
    elif isinstance(data, (dict, AutotaskModel)):
        item = _to_dict(data)
        if as_json:
            click.echo(json.dumps(item, indent=2, default=str))
        else:
            _print_record(item)
    else:
        click.echo(data)


def _to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, AutotaskModel):
        return item.model_dump(mode="json", exclude_none=True)
    if isinstance(item, dict):
        return item
    return {"value": item}


def _print_table(items: list[dict[str, Any]]) -> None:
    """Simple table printer for terminal output."""
    if not items:
        click.echo("No results.")
        return
    keys = list(items[0].keys())
    widths = {k: len(k) for k in keys}
    for item in items:
        for k in keys:
            val = str(item.get(k, ""))
            widths[k] = max(widths[k], min(len(val), 50))
    header = "  ".join(k.ljust(widths[k])[:widths[k]] for k in keys)
    click.echo(header)
    click.echo("  ".join("-" * widths[k] for k in keys))
    for item in items:
        row = "  ".join(str(item.get(k, "")).ljust(widths[k])[:widths[k]] for k in keys)
        click.echo(row)
    click.echo(f"\n({len(items)} records)")


def _print_record(item: dict[str, Any]) -> None:
    """Print a single record as key: value pairs."""
    max_key = max(len(k) for k in item) if item else 0
    for k, v in item.items():
        click.echo(f"  {k.rjust(max_key)}: {v}")


def _get_client_and_manager() -> tuple[AutotaskClient, EntityManager]:
    """Create client and entity manager from env config."""
    config = AutotaskConfig.from_env()
    client = AutotaskClient(config)
    manager = EntityManager(client)
    return client, manager


async def _with_client(callback: Any) -> Any:
    """Run a callback within a connected client context."""
    client, manager = _get_client_and_manager()
    async with client:
        return await callback(manager)


def _parse_filters(filter_args: tuple[str, ...]) -> list[Q]:
    """Parse CLI filter args like 'status=8' or 'id__gt=100' into Q objects."""
    filters = []
    for arg in filter_args:
        if "=" not in arg:
            raise click.BadParameter(f"Filter must be key=value or key__op=value: {arg}")
        key, val = arg.split("=", 1)
        # Try to parse value as int, then float, then leave as string
        typed_val: Any = val
        try:
            typed_val = int(val)
        except ValueError:
            try:
                typed_val = float(val)
            except ValueError:
                if val.lower() == "true":
                    typed_val = True
                elif val.lower() == "false":
                    typed_val = False
        filters.append(Q(**{key: typed_val}))
    return filters


# ── Root group ──────────────────────────────────────────────────

@click.group()
@click.option("--json/--table", "use_json", default=True, help="Output format (default: JSON)")
@click.pass_context
def cli(ctx: click.Context, use_json: bool) -> None:
    """Autotask REST API client."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json


# ── Tickets ─────────────────────────────────────────────────────

@cli.group()
def tickets() -> None:
    """Ticket operations."""


@tickets.command("list")
@click.option("--status", type=int, help="Filter by status ID")
@click.option("--queue", type=int, help="Filter by queue ID")
@click.option("--assigned-to", type=int, help="Filter by assigned resource ID")
@click.option("--company", type=int, help="Filter by company ID")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.argument("filters", nargs=-1)
@click.pass_context
def tickets_list(
    ctx: click.Context,
    status: int | None,
    queue: int | None,
    assigned_to: int | None,
    company: int | None,
    limit: int,
    filters: tuple[str, ...],
) -> None:
    """List tickets. Extra filters as key=value args."""
    q_filters = _parse_filters(filters)
    if status is not None:
        q_filters.append(Q(status=status))
    if queue is not None:
        q_filters.append(Q(queueID=queue))
    if assigned_to is not None:
        q_filters.append(Q(assignedResourceID=assigned_to))
    if company is not None:
        q_filters.append(Q(companyID=company))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(Ticket, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@tickets.command("get")
@click.argument("ticket_id", type=int)
@click.pass_context
def tickets_get(ctx: click.Context, ticket_id: int) -> None:
    """Get a ticket by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(Ticket, ticket_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@tickets.command("create")
@click.option("--title", required=True, help="Ticket title")
@click.option("--company-id", required=True, type=int, help="Company ID")
@click.option("--status", type=int, default=1, help="Status ID (default: 1=New)")
@click.option("--priority", type=int, default=2, help="Priority ID (default: 2=Medium)")
@click.option("--queue", type=int, help="Queue ID")
@click.option("--description", help="Ticket description")
@click.option("--assigned-to", type=int, help="Assigned resource ID")
@click.pass_context
def tickets_create(
    ctx: click.Context,
    title: str,
    company_id: int,
    status: int,
    priority: int,
    queue: int | None,
    description: str | None,
    assigned_to: int | None,
) -> None:
    """Create a new ticket."""
    ticket = Ticket(
        title=title,
        companyID=company_id,
        status=status,
        priority=priority,
        queueID=queue,
        description=description,
        assignedResourceID=assigned_to,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(ticket)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@tickets.command("update")
@click.argument("ticket_id", type=int)
@click.option("--status", type=int, help="Status ID")
@click.option("--priority", type=int, help="Priority ID")
@click.option("--queue", type=int, help="Queue ID")
@click.option("--assigned-to", type=int, help="Assigned resource ID")
@click.option("--title", help="Ticket title")
@click.pass_context
def tickets_update(
    ctx: click.Context,
    ticket_id: int,
    status: int | None,
    priority: int | None,
    queue: int | None,
    assigned_to: int | None,
    title: str | None,
) -> None:
    """Update a ticket by ID (PATCH — only specified fields change)."""
    fields: dict[str, Any] = {"id": ticket_id}
    if status is not None:
        fields["status"] = status
    if priority is not None:
        fields["priority"] = priority
    if queue is not None:
        fields["queueID"] = queue
    if assigned_to is not None:
        fields["assignedResourceID"] = assigned_to
    if title is not None:
        fields["title"] = title

    ticket = Ticket(**fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(ticket)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


# ── Companies ───────────────────────────────────────────────────

@cli.group()
def companies() -> None:
    """Company operations."""


@companies.command("list")
@click.option("--search", help="Search by company name (contains)")
@click.option("--active/--all", default=True, help="Active only (default) or all")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.argument("filters", nargs=-1)
@click.pass_context
def companies_list(
    ctx: click.Context,
    search: str | None,
    active: bool,
    limit: int,
    filters: tuple[str, ...],
) -> None:
    """List companies."""
    q_filters = _parse_filters(filters)
    if search:
        q_filters.append(Q(companyName__contains=search))
    if active:
        q_filters.append(Q(isActive=True))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(Company, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@companies.command("get")
@click.argument("company_id", type=int)
@click.pass_context
def companies_get(ctx: click.Context, company_id: int) -> None:
    """Get a company by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(Company, company_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Resources ───────────────────────────────────────────────────

@cli.group()
def resources() -> None:
    """Resource (user/technician) operations."""


@resources.command("list")
@click.option("--search", help="Search by name (firstName or lastName contains)")
@click.option("--active/--all", default=True, help="Active only (default) or all")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.pass_context
def resources_list(
    ctx: click.Context,
    search: str | None,
    active: bool,
    limit: int,
) -> None:
    """List resources."""
    q_filters: list[Q] = []
    if search:
        q_filters.append(Q(lastName__contains=search))
    if active:
        q_filters.append(Q(isActive=True))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(Resource, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@resources.command("get")
@click.argument("resource_id", type=int)
@click.pass_context
def resources_get(ctx: click.Context, resource_id: int) -> None:
    """Get a resource by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(Resource, resource_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Projects ────────────────────────────────────────────────────

@cli.group()
def projects() -> None:
    """Project operations."""


@projects.command("list")
@click.option("--company", type=int, help="Filter by company ID")
@click.option("--status", type=int, help="Filter by status ID")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.argument("filters", nargs=-1)
@click.pass_context
def projects_list(
    ctx: click.Context,
    company: int | None,
    status: int | None,
    limit: int,
    filters: tuple[str, ...],
) -> None:
    """List projects."""
    q_filters = _parse_filters(filters)
    if company is not None:
        q_filters.append(Q(companyID=company))
    if status is not None:
        q_filters.append(Q(status=status))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(Project, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@projects.command("get")
@click.argument("project_id", type=int)
@click.pass_context
def projects_get(ctx: click.Context, project_id: int) -> None:
    """Get a project by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(Project, project_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Time Entries ────────────────────────────────────────────────

@cli.group("time-entries")
def time_entries() -> None:
    """Time entry operations."""


@time_entries.command("list")
@click.option("--resource", type=int, help="Filter by resource ID")
@click.option("--ticket", type=int, help="Filter by ticket ID")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.argument("filters", nargs=-1)
@click.pass_context
def time_entries_list(
    ctx: click.Context,
    resource: int | None,
    ticket: int | None,
    limit: int,
    filters: tuple[str, ...],
) -> None:
    """List time entries."""
    q_filters = _parse_filters(filters)
    if resource is not None:
        q_filters.append(Q(resourceID=resource))
    if ticket is not None:
        q_filters.append(Q(ticketID=ticket))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(TimeEntry, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@time_entries.command("get")
@click.argument("entry_id", type=int)
@click.pass_context
def time_entries_get(ctx: click.Context, entry_id: int) -> None:
    """Get a time entry by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(TimeEntry, entry_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Generic query (any entity) ──────────────────────────────────

@cli.command("query")
@click.argument("entity_type")
@click.argument("filters", nargs=-1)
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.option("--parent-id", type=int, help="Parent entity ID (for child entities)")
@click.pass_context
def generic_query(
    ctx: click.Context,
    entity_type: str,
    filters: tuple[str, ...],
    limit: int,
    parent_id: int | None,
) -> None:
    """Query any entity type. Uses registered model if available, raw dicts otherwise.

    Examples:

        autotask query Tickets status=8 queueID=29975869

        autotask query ConfigurationItems isActive=true
    """
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type
    q_filters = _parse_filters(filters)

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(target, *q_filters, parent_id=parent_id, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


# ── Entity info / field inspection ──────────────────────────────

@cli.command("info")
@click.argument("entity_type")
@click.pass_context
def entity_info(ctx: click.Context, entity_type: str) -> None:
    """Show entity capabilities (canCreate, canQuery, etc.)."""
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _fetch(em: EntityManager) -> dict[str, Any]:
        return await em.entity_info(target)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@cli.command("fields")
@click.argument("entity_type")
@click.pass_context
def field_info(ctx: click.Context, entity_type: str) -> None:
    """Show field definitions for an entity type."""
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _fetch(em: EntityManager) -> dict[str, Any]:
        return await em.field_info(target)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Config check ────────────────────────────────────────────────

@cli.command("config")
def show_config() -> None:
    """Show current configuration status (no secrets)."""
    try:
        config = AutotaskConfig.from_env()
        click.echo(json.dumps({
            "username": config.username,
            "api_url": config.api_url or "(will discover via zone lookup)",
            "resource_id": config.resource_id,
            "has_secret": bool(config.secret),
            "has_integration_code": bool(config.integration_code),
        }, indent=2))
    except ValueError as e:
        click.echo(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)


# ── Error handling wrapper ──────────────────────────────────────

def _safe_cli() -> None:
    """Entrypoint with error handling."""
    try:
        cli(standalone_mode=False)
    except AutotaskAuthError as e:
        click.echo(json.dumps({"error": "auth", "message": str(e)}), err=True)
        sys.exit(1)
    except AutotaskNotFoundError as e:
        click.echo(json.dumps({"error": "not_found", "message": str(e)}), err=True)
        sys.exit(1)
    except AutotaskAPIError as e:
        click.echo(json.dumps({"error": "api", "message": str(e)}), err=True)
        sys.exit(1)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except ValueError as e:
        click.echo(json.dumps({"error": "validation", "message": str(e)}), err=True)
        sys.exit(1)
