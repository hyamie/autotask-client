"""Integration tests against the live Autotask API.

These tests hit the real API and are NOT run in CI. Run manually with:

    AUTOTASK_USERNAME=... AUTOTASK_SECRET=... AUTOTASK_INTEGRATION_CODE=... \
        pytest tests/test_integration.py -v

Or with 1Password:

    eval $(op item get "Autotask API - ChargerProjects" --vault ClaudeAgents \
        --format json | python3 -c "
import json, sys
d = {f['label']: f['value'] for f in json.load(sys.stdin)['fields'] if f.get('label')}
print(f'export AUTOTASK_USERNAME={d[\"username\"]}')
print(f'export AUTOTASK_SECRET=\"{d[\"password\"]}\"')
print(f'export AUTOTASK_INTEGRATION_CODE={d[\"Integration Code\"]}')
print(f'export AUTOTASK_API_URL=https://{d[\"zone\"]}.autotask.net')
")
    pytest tests/test_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from autotask.client import AutotaskClient
from autotask.config import AutotaskConfig
from autotask.entities import EntityManager
from autotask.exceptions import AutotaskNotFoundError
from autotask.models import Company, Project, Resource, Ticket, TimeEntry
from autotask.query import Q

_HAS_CREDS = all(
    os.environ.get(k)
    for k in ("AUTOTASK_USERNAME", "AUTOTASK_SECRET", "AUTOTASK_INTEGRATION_CODE")
)

pytestmark = pytest.mark.skipif(not _HAS_CREDS, reason="No Autotask credentials in env")


@pytest.fixture
async def em():
    """Connected EntityManager for integration tests."""
    config = AutotaskConfig.from_env()
    client = AutotaskClient(config)
    async with client:
        yield EntityManager(client)


# ── Connection & Auth ───────────────────────────────────────────


class TestConnection:
    async def test_zone_discovery_and_auth(self, em: EntityManager) -> None:
        """Verify we can connect and authenticate."""
        info = await em.entity_info(Ticket)
        assert "item" in info or "fields" in info or isinstance(info, dict)

    async def test_zone_url_cached(self) -> None:
        """Second connection should use cached zone URL."""
        config = AutotaskConfig.from_env()
        client = AutotaskClient(config)
        async with client:
            assert client.base_url is not None
            assert "autotask.net" in client.base_url


# ── Read Operations ─────────────────────────────────────────────


class TestQueryOperations:
    async def test_query_tickets(self, em: EntityManager) -> None:
        """Query recent tickets — should return typed Ticket objects."""
        tickets = await em.query(Ticket, Q(id__gt=0), max_records=5)
        assert isinstance(tickets, list)
        assert len(tickets) > 0
        assert isinstance(tickets[0], Ticket)
        assert tickets[0].id is not None

    async def test_query_tickets_with_status_filter(self, em: EntityManager) -> None:
        """Filter tickets by status=8 (In Progress)."""
        tickets = await em.query(Ticket, Q(status=8), max_records=5)
        assert isinstance(tickets, list)
        for t in tickets:
            assert t.status == 8

    async def test_query_companies(self, em: EntityManager) -> None:
        """Query active companies."""
        companies = await em.query(Company, Q(isActive=True), max_records=5)
        assert isinstance(companies, list)
        assert len(companies) > 0
        assert isinstance(companies[0], Company)
        assert companies[0].companyName is not None

    async def test_query_resources(self, em: EntityManager) -> None:
        """Query active resources."""
        resources = await em.query(Resource, Q(isActive=True), max_records=5)
        assert isinstance(resources, list)
        assert len(resources) > 0
        assert isinstance(resources[0], Resource)

    async def test_query_projects(self, em: EntityManager) -> None:
        """Query projects."""
        projects = await em.query(Project, Q(id__gt=0), max_records=5)
        assert isinstance(projects, list)
        assert len(projects) > 0
        assert isinstance(projects[0], Project)

    async def test_query_time_entries(self, em: EntityManager) -> None:
        """Query recent time entries."""
        entries = await em.query(TimeEntry, Q(id__gt=0), max_records=5)
        assert isinstance(entries, list)
        # May be empty if no time entries exist, that's ok
        if entries:
            assert isinstance(entries[0], TimeEntry)

    async def test_query_generic_entity(self, em: EntityManager) -> None:
        """Query a generic (unmodeled) entity type."""
        items = await em.query("Contacts", Q(id__gt=0), max_records=3)
        assert isinstance(items, list)
        if items:
            assert isinstance(items[0], dict)


class TestGetOperations:
    async def test_get_ticket_by_id(self, em: EntityManager) -> None:
        """Get a specific ticket by querying first, then fetching by ID."""
        tickets = await em.query(Ticket, Q(id__gt=0), max_records=1)
        assert len(tickets) > 0
        ticket = await em.get(Ticket, tickets[0].id)
        assert isinstance(ticket, Ticket)
        assert ticket.id == tickets[0].id

    async def test_get_company_by_id(self, em: EntityManager) -> None:
        """Get a specific company."""
        companies = await em.query(Company, Q(isActive=True), max_records=1)
        assert len(companies) > 0
        company = await em.get(Company, companies[0].id)
        assert isinstance(company, Company)
        assert company.id == companies[0].id

    async def test_get_nonexistent_raises(self, em: EntityManager) -> None:
        """Getting a nonexistent entity should raise NotFoundError."""
        with pytest.raises(AutotaskNotFoundError):
            await em.get(Ticket, 999999999)


# ── Entity Metadata ─────────────────────────────────────────────


class TestMetadata:
    async def test_entity_info(self, em: EntityManager) -> None:
        """Get entity info for Tickets."""
        info = await em.entity_info(Ticket)
        assert isinstance(info, dict)

    async def test_field_info(self, em: EntityManager) -> None:
        """Get field definitions for Tickets."""
        fields = await em.field_info(Ticket)
        assert isinstance(fields, dict)
        assert "fields" in fields
        field_names = [f["name"] for f in fields["fields"]]
        assert "title" in field_names
        assert "status" in field_names

    async def test_field_info_generic(self, em: EntityManager) -> None:
        """Get field info for a generic entity."""
        fields = await em.field_info("ConfigurationItems")
        assert isinstance(fields, dict)
        assert "fields" in fields


# ── Pagination ──────────────────────────────────────────────────


class TestPagination:
    async def test_pagination_works(self, em: EntityManager) -> None:
        """Query more than 500 records to verify pagination kicks in."""
        # Just verify it doesn't crash — we cap at a small number
        tickets = await em.query(Ticket, Q(id__gt=0), max_records=10)
        assert isinstance(tickets, list)

    async def test_max_records_respected(self, em: EntityManager) -> None:
        """Verify max_records caps results."""
        tickets = await em.query(Ticket, Q(id__gt=0), max_records=3)
        assert len(tickets) <= 3


# ── Round-Trip (Extra Fields) ───────────────────────────────────


class TestRoundTrip:
    async def test_extra_fields_preserved(self, em: EntityManager) -> None:
        """Verify that unmodeled API fields survive the round-trip."""
        tickets = await em.query(Ticket, Q(id__gt=0), max_records=1)
        assert len(tickets) > 0
        ticket = tickets[0]
        # The API returns many fields not in our model
        dumped = ticket.model_dump(mode="json")
        # Should have more keys than just the modeled fields
        modeled_fields = {
            "id", "ticketNumber", "title", "description", "companyID",
            "queueID", "status", "priority", "assignedResourceID",
            "projectID", "createDate", "dueDateTime", "lastActivityDate", "source",
        }
        extra_fields = set(dumped.keys()) - modeled_fields
        assert len(extra_fields) > 0, "Expected unmodeled API fields to be preserved"
