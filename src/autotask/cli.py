"""CLI wrapper for Autotask REST API client.

Thin Click wrapper over the library. Primary consumer is Claude Code,
so JSON output is the default. Use --table for human-readable output.
"""

from __future__ import annotations

import asyncio
import json
import re
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
    ProjectNote,
    Resource,
    Task,
    TaskNote,
    Ticket,
    TicketNote,
    TimeEntry,
)
from autotask.models.base import AutotaskModel, get_model_class
from autotask.query import Q

_ENTITY_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,60}$")
_FIELD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{0,60}$")


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
        raw_field = key.split("__")[0] if "__" in key else key
        if not _FIELD_NAME_RE.fullmatch(raw_field):
            raise click.BadParameter(f"Invalid field name: {raw_field}")
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


def _validate_entity_name(entity_type: str) -> None:
    """Validate entity type name to prevent path injection."""
    if not _ENTITY_NAME_RE.fullmatch(entity_type):
        raise click.BadParameter(
            f"Invalid entity name: {entity_type}. Use PascalCase (e.g., Tickets, Companies)."
        )


def _parse_json_fields(fields_json: str) -> dict[str, Any]:
    """Parse a JSON string of fields."""
    try:
        data = json.loads(fields_json)
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise click.BadParameter("Fields must be a JSON object")
    return data


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


@tickets.command("delete")
@click.argument("ticket_id", type=int)
@click.pass_context
def tickets_delete(ctx: click.Context, ticket_id: int) -> None:
    """Delete a ticket by ID."""

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(Ticket, ticket_id)
        return {"status": "deleted", "entity": "Tickets", "id": ticket_id}

    result = _run(_with_client(_del))
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


@companies.command("create")
@click.option("--name", "company_name", required=True, help="Company name")
@click.option("--type", "company_type", type=int, help="Company type ID")
@click.option("--phone", help="Phone number")
@click.option("--owner", type=int, help="Owner resource ID")
@click.pass_context
def companies_create(
    ctx: click.Context,
    company_name: str,
    company_type: int | None,
    phone: str | None,
    owner: int | None,
) -> None:
    """Create a new company."""
    company = Company(
        companyName=company_name,
        companyType=company_type,
        phone=phone,
        ownerResourceID=owner,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(company)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@companies.command("update")
@click.argument("company_id", type=int)
@click.option("--name", "company_name", help="Company name")
@click.option("--phone", help="Phone number")
@click.option("--owner", type=int, help="Owner resource ID")
@click.pass_context
def companies_update(
    ctx: click.Context,
    company_id: int,
    company_name: str | None,
    phone: str | None,
    owner: int | None,
) -> None:
    """Update a company by ID."""
    fields: dict[str, Any] = {"id": company_id}
    if company_name is not None:
        fields["companyName"] = company_name
    if phone is not None:
        fields["phone"] = phone
    if owner is not None:
        fields["ownerResourceID"] = owner

    company = Company(**fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(company)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


@companies.command("delete")
@click.argument("company_id", type=int)
@click.pass_context
def companies_delete(ctx: click.Context, company_id: int) -> None:
    """Delete a company by ID."""

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(Company, company_id)
        return {"status": "deleted", "entity": "Companies", "id": company_id}

    result = _run(_with_client(_del))
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


@projects.command("create")
@click.option("--name", "project_name", required=True, help="Project name")
@click.option("--company-id", required=True, type=int, help="Company ID")
@click.option("--type", "project_type", type=int, help="Project type ID")
@click.option("--status", type=int, default=1, help="Status ID (default: 1)")
@click.option("--lead", type=int, help="Project lead resource ID")
@click.option("--description", help="Project description")
@click.pass_context
def projects_create(
    ctx: click.Context,
    project_name: str,
    company_id: int,
    project_type: int | None,
    status: int,
    lead: int | None,
    description: str | None,
) -> None:
    """Create a new project."""
    project = Project(
        projectName=project_name,
        companyID=company_id,
        projectType=project_type,
        status=status,
        projectLeadResourceID=lead,
        description=description,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(project)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@projects.command("update")
@click.argument("project_id", type=int)
@click.option("--name", "project_name", help="Project name")
@click.option("--status", type=int, help="Status ID")
@click.option("--lead", type=int, help="Project lead resource ID")
@click.option("--description", help="Description")
@click.pass_context
def projects_update(
    ctx: click.Context,
    project_id: int,
    project_name: str | None,
    status: int | None,
    lead: int | None,
    description: str | None,
) -> None:
    """Update a project by ID."""
    fields: dict[str, Any] = {"id": project_id}
    if project_name is not None:
        fields["projectName"] = project_name
    if status is not None:
        fields["status"] = status
    if lead is not None:
        fields["projectLeadResourceID"] = lead
    if description is not None:
        fields["description"] = description

    project = Project(**fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(project)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


@projects.command("delete")
@click.argument("project_id", type=int)
@click.pass_context
def projects_delete(ctx: click.Context, project_id: int) -> None:
    """Delete a project by ID."""

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(Project, project_id)
        return {"status": "deleted", "entity": "Projects", "id": project_id}

    result = _run(_with_client(_del))
    _output(result, as_json=ctx.obj["json"])


# ── Tasks ──────────────────────────────────────────────────────

@cli.group()
def tasks() -> None:
    """Task operations (queried via projectID filter, not child entity)."""


@tasks.command("list")
@click.option("--project", type=int, help="Filter by project ID")
@click.option("--status", type=int, help="Filter by status ID")
@click.option("--assigned-to", type=int, help="Filter by assigned resource ID")
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.argument("filters", nargs=-1)
@click.pass_context
def tasks_list(
    ctx: click.Context,
    project: int | None,
    status: int | None,
    assigned_to: int | None,
    limit: int,
    filters: tuple[str, ...],
) -> None:
    """List tasks."""
    q_filters = _parse_filters(filters)
    if project is not None:
        q_filters.append(Q(projectID=project))
    if status is not None:
        q_filters.append(Q(status=status))
    if assigned_to is not None:
        q_filters.append(Q(assignedResourceID=assigned_to))

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(Task, *q_filters, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@tasks.command("get")
@click.argument("task_id", type=int)
@click.pass_context
def tasks_get(ctx: click.Context, task_id: int) -> None:
    """Get a task by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(Task, task_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@tasks.command("create")
@click.option("--project-id", required=True, type=int, help="Project ID")
@click.option("--title", required=True, help="Task title")
@click.option("--status", type=int, default=1, help="Status ID (default: 1)")
@click.option("--assigned-to", type=int, help="Assigned resource ID")
@click.option("--description", help="Task description")
@click.option("--estimated-hours", type=float, help="Estimated hours")
@click.pass_context
def tasks_create(
    ctx: click.Context,
    project_id: int,
    title: str,
    status: int,
    assigned_to: int | None,
    description: str | None,
    estimated_hours: float | None,
) -> None:
    """Create a new task."""
    task = Task(
        projectID=project_id,
        title=title,
        status=status,
        assignedResourceID=assigned_to,
        description=description,
        estimatedHours=estimated_hours,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(task)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@tasks.command("update")
@click.argument("task_id", type=int)
@click.option("--title", help="Task title")
@click.option("--status", type=int, help="Status ID")
@click.option("--assigned-to", type=int, help="Assigned resource ID")
@click.option("--description", help="Description")
@click.pass_context
def tasks_update(
    ctx: click.Context,
    task_id: int,
    title: str | None,
    status: int | None,
    assigned_to: int | None,
    description: str | None,
) -> None:
    """Update a task by ID."""
    fields: dict[str, Any] = {"id": task_id}
    if title is not None:
        fields["title"] = title
    if status is not None:
        fields["status"] = status
    if assigned_to is not None:
        fields["assignedResourceID"] = assigned_to
    if description is not None:
        fields["description"] = description

    task = Task(**fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(task)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


@tasks.command("delete")
@click.argument("task_id", type=int)
@click.pass_context
def tasks_delete(ctx: click.Context, task_id: int) -> None:
    """Delete a task by ID."""

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(Task, task_id)
        return {"status": "deleted", "entity": "Tasks", "id": task_id}

    result = _run(_with_client(_del))
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


@time_entries.command("create")
@click.option("--resource-id", required=True, type=int, help="Resource ID")
@click.option("--ticket-id", type=int, help="Ticket ID")
@click.option("--task-id", type=int, help="Task ID")
@click.option("--hours", required=True, type=float, help="Hours worked")
@click.option("--summary", help="Summary notes")
@click.option("--date", "date_worked", help="Date worked (YYYY-MM-DD)")
@click.pass_context
def time_entries_create(
    ctx: click.Context,
    resource_id: int,
    ticket_id: int | None,
    task_id: int | None,
    hours: float,
    summary: str | None,
    date_worked: str | None,
) -> None:
    """Create a new time entry."""
    entry = TimeEntry(
        resourceID=resource_id,
        ticketID=ticket_id,
        taskID=task_id,
        hoursWorked=hours,
        summaryNotes=summary,
        dateWorked=date_worked,  # type: ignore[arg-type]
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(entry)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@time_entries.command("update")
@click.argument("entry_id", type=int)
@click.option("--hours", type=float, help="Hours worked")
@click.option("--summary", help="Summary notes")
@click.pass_context
def time_entries_update(
    ctx: click.Context,
    entry_id: int,
    hours: float | None,
    summary: str | None,
) -> None:
    """Update a time entry by ID."""
    fields: dict[str, Any] = {"id": entry_id}
    if hours is not None:
        fields["hoursWorked"] = hours
    if summary is not None:
        fields["summaryNotes"] = summary

    entry = TimeEntry(**fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(entry)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


@time_entries.command("delete")
@click.argument("entry_id", type=int)
@click.pass_context
def time_entries_delete(ctx: click.Context, entry_id: int) -> None:
    """Delete a time entry by ID."""

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(TimeEntry, entry_id)
        return {"status": "deleted", "entity": "TimeEntries", "id": entry_id}

    result = _run(_with_client(_del))
    _output(result, as_json=ctx.obj["json"])


# ── Ticket Notes ───────────────────────────────────────────────

@cli.group("ticket-notes")
def ticket_notes() -> None:
    """Ticket note operations (child of ticket)."""


@ticket_notes.command("list")
@click.argument("ticket_id", type=int)
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.pass_context
def ticket_notes_list(ctx: click.Context, ticket_id: int, limit: int) -> None:
    """List notes for a ticket."""

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(TicketNote, parent_id=ticket_id, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@ticket_notes.command("get")
@click.argument("ticket_id", type=int)
@click.argument("note_id", type=int)
@click.pass_context
def ticket_notes_get(ctx: click.Context, ticket_id: int, note_id: int) -> None:
    """Get a ticket note by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(TicketNote, note_id, parent_id=ticket_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@ticket_notes.command("create")
@click.argument("ticket_id", type=int)
@click.option("--title", required=True, help="Note title")
@click.option("--description", required=True, help="Note body")
@click.option("--publish", type=int, default=1, help="Publish type (default: 1)")
@click.pass_context
def ticket_notes_create(
    ctx: click.Context,
    ticket_id: int,
    title: str,
    description: str,
    publish: int,
) -> None:
    """Create a note on a ticket."""
    note = TicketNote(
        ticketID=ticket_id,
        title=title,
        description=description,
        publish=publish,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(note, parent_id=ticket_id)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


# ── Project Notes ──────────────────────────────────────────────

@cli.group("project-notes")
def project_notes() -> None:
    """Project note operations (child of project)."""


@project_notes.command("list")
@click.argument("project_id", type=int)
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.pass_context
def project_notes_list(ctx: click.Context, project_id: int, limit: int) -> None:
    """List notes for a project."""

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(ProjectNote, parent_id=project_id, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@project_notes.command("get")
@click.argument("project_id", type=int)
@click.argument("note_id", type=int)
@click.pass_context
def project_notes_get(ctx: click.Context, project_id: int, note_id: int) -> None:
    """Get a project note by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(ProjectNote, note_id, parent_id=project_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@project_notes.command("create")
@click.argument("project_id", type=int)
@click.option("--title", required=True, help="Note title")
@click.option("--description", required=True, help="Note body")
@click.option("--publish", type=int, default=1, help="Publish type (default: 1)")
@click.pass_context
def project_notes_create(
    ctx: click.Context,
    project_id: int,
    title: str,
    description: str,
    publish: int,
) -> None:
    """Create a note on a project."""
    note = ProjectNote(
        projectID=project_id,
        title=title,
        description=description,
        publish=publish,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(note, parent_id=project_id)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


# ── Task Notes ─────────────────────────────────────────────────

@cli.group("task-notes")
def task_notes() -> None:
    """Task note operations (child of task)."""


@task_notes.command("list")
@click.argument("task_id", type=int)
@click.option("--limit", type=int, default=50, help="Max records (default: 50)")
@click.pass_context
def task_notes_list(ctx: click.Context, task_id: int, limit: int) -> None:
    """List notes for a task."""

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(TaskNote, parent_id=task_id, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@task_notes.command("get")
@click.argument("task_id", type=int)
@click.argument("note_id", type=int)
@click.pass_context
def task_notes_get(ctx: click.Context, task_id: int, note_id: int) -> None:
    """Get a task note by ID."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(TaskNote, note_id, parent_id=task_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@task_notes.command("create")
@click.argument("task_id", type=int)
@click.option("--title", required=True, help="Note title")
@click.option("--description", required=True, help="Note body")
@click.option("--publish", type=int, default=1, help="Publish type (default: 1)")
@click.pass_context
def task_notes_create(
    ctx: click.Context,
    task_id: int,
    title: str,
    description: str,
    publish: int,
) -> None:
    """Create a note on a task."""
    note = TaskNote(
        taskID=task_id,
        title=title,
        description=description,
        publish=publish,
    )

    async def _create(em: EntityManager) -> Any:
        return await em.create(note, parent_id=task_id)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


# ── Generic CRUD (any entity) ──────────────────────────────────

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
    _validate_entity_name(entity_type)
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type
    q_filters = _parse_filters(filters)

    async def _run_query(em: EntityManager) -> list[Any]:
        return await em.query(target, *q_filters, parent_id=parent_id, max_records=limit)

    result = _run(_with_client(_run_query))
    _output(result, as_json=ctx.obj["json"])


@cli.command("get")
@click.argument("entity_type")
@click.argument("entity_id", type=int)
@click.option("--parent-id", type=int, help="Parent entity ID (for child entities)")
@click.pass_context
def generic_get(
    ctx: click.Context,
    entity_type: str,
    entity_id: int,
    parent_id: int | None,
) -> None:
    """Get any entity by type and ID.

    Examples:

        autotask get Tickets 12345

        autotask get TicketNotes 67890 --parent-id 12345
    """
    _validate_entity_name(entity_type)
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _fetch(em: EntityManager) -> Any:
        return await em.get(target, entity_id, parent_id=parent_id)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


@cli.command("create")
@click.argument("entity_type")
@click.option("--fields", "fields_json", required=True, help='JSON object of fields (e.g. \'{"title":"Test"}\')')
@click.option("--parent-id", type=int, help="Parent entity ID (for child entities)")
@click.pass_context
def generic_create(
    ctx: click.Context,
    entity_type: str,
    fields_json: str,
    parent_id: int | None,
) -> None:
    """Create any entity from JSON fields.

    Examples:

        autotask create Tickets --fields '{"title":"Test","companyID":123,"status":1,"priority":2}'
    """
    _validate_entity_name(entity_type)
    model_class = get_model_class(entity_type)
    if model_class is None:
        click.echo(json.dumps({"error": f"No model registered for: {entity_type}"}), err=True)
        sys.exit(1)
    fields = _parse_json_fields(fields_json)
    instance = model_class.model_validate(fields)

    async def _create(em: EntityManager) -> Any:
        return await em.create(instance, parent_id=parent_id)

    result = _run(_with_client(_create))
    _output(result, as_json=ctx.obj["json"])


@cli.command("update")
@click.argument("entity_type")
@click.argument("entity_id", type=int)
@click.option("--fields", "fields_json", required=True, help='JSON object of fields to update')
@click.option("--parent-id", type=int, help="Parent entity ID (for child entities)")
@click.pass_context
def generic_update(
    ctx: click.Context,
    entity_type: str,
    entity_id: int,
    fields_json: str,
    parent_id: int | None,
) -> None:
    """Update any entity by type and ID (PATCH).

    Examples:

        autotask update Tickets 12345 --fields '{"status":5,"priority":1}'
    """
    _validate_entity_name(entity_type)
    model_class = get_model_class(entity_type)
    if model_class is None:
        click.echo(json.dumps({"error": f"No model registered for: {entity_type}"}), err=True)
        sys.exit(1)
    fields = _parse_json_fields(fields_json)
    fields["id"] = entity_id
    instance = model_class.model_validate(fields)

    async def _update(em: EntityManager) -> Any:
        return await em.update(instance, parent_id=parent_id)

    result = _run(_with_client(_update))
    _output(result, as_json=ctx.obj["json"])


@cli.command("delete")
@click.argument("entity_type")
@click.argument("entity_id", type=int)
@click.option("--parent-id", type=int, help="Parent entity ID (for child entities)")
@click.pass_context
def generic_delete(
    ctx: click.Context,
    entity_type: str,
    entity_id: int,
    parent_id: int | None,
) -> None:
    """Delete any entity by type and ID.

    Examples:

        autotask delete Tickets 12345
    """
    _validate_entity_name(entity_type)
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _del(em: EntityManager) -> dict[str, Any]:
        await em.delete(target, entity_id, parent_id=parent_id)
        return {"status": "deleted", "entity": entity_type, "id": entity_id}

    result = _run(_with_client(_del))
    _output(result, as_json=ctx.obj["json"])


# ── Entity info / field inspection ──────────────────────────────

@cli.command("info")
@click.argument("entity_type")
@click.pass_context
def entity_info(ctx: click.Context, entity_type: str) -> None:
    """Show entity capabilities (canCreate, canQuery, etc.)."""
    _validate_entity_name(entity_type)
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
    _validate_entity_name(entity_type)
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _fetch(em: EntityManager) -> dict[str, Any]:
        return await em.field_info(target)

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Whoami ──────────────────────────────────────────────────────

@cli.command("whoami")
@click.pass_context
def whoami(ctx: click.Context) -> None:
    """Show the authenticated user's resource record."""

    async def _fetch(em: EntityManager) -> Any:
        return await em.whoami()

    result = _run(_with_client(_fetch))
    _output(result, as_json=ctx.obj["json"])


# ── Picklist ────────────────────────────────────────────────────

@cli.command("picklist")
@click.argument("entity_type")
@click.argument("field_name")
@click.pass_context
def picklist(ctx: click.Context, entity_type: str, field_name: str) -> None:
    """Resolve picklist values for an entity field.

    Examples:

        autotask picklist Tickets status

        autotask picklist Tickets priority
    """
    _validate_entity_name(entity_type)
    model = get_model_class(entity_type)
    target: type[AutotaskModel] | str = model if model else entity_type

    async def _fetch(em: EntityManager) -> dict[int, str]:
        return await em.resolve_picklist(target, field_name)

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
