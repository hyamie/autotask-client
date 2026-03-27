"""Tests for the EntityManager."""

from unittest.mock import AsyncMock

import pytest

from autotask.entities.manager import EntityManager
from autotask.models import Company, ProjectNote, Resource, Ticket, TicketNote
from autotask.query import Q


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def manager(mock_client):
    return EntityManager(mock_client)


class TestGet:
    @pytest.mark.asyncio
    async def test_typed(self, manager, mock_client):
        mock_client.get.return_value = {
            "item": {"id": 123, "title": "Test", "status": 1, "companyID": 456}
        }
        result = await manager.get(Ticket, 123)
        assert isinstance(result, Ticket)
        assert result.id == 123
        assert result.title == "Test"
        mock_client.get.assert_called_once_with("Tickets/123")

    @pytest.mark.asyncio
    async def test_generic_string(self, manager, mock_client):
        mock_client.get.return_value = {"item": {"id": 1, "name": "Test"}}
        result = await manager.get("SomeEntity", 1)
        assert isinstance(result, dict)
        assert result["id"] == 1
        mock_client.get.assert_called_once_with("SomeEntity/1")

    @pytest.mark.asyncio
    async def test_child_entity(self, manager, mock_client):
        mock_client.get.return_value = {
            "item": {"id": 1, "ticketID": 100, "title": "Note 1"}
        }
        result = await manager.get(TicketNote, 1, parent_id=100)
        assert isinstance(result, TicketNote)
        mock_client.get.assert_called_once_with("Tickets/100/Notes/1")

    @pytest.mark.asyncio
    async def test_child_without_parent_uses_flat_path(self, manager, mock_client):
        mock_client.get.return_value = {
            "item": {"id": 1, "ticketID": 100, "title": "Note 1"}
        }
        result = await manager.get(TicketNote, 1)
        assert isinstance(result, TicketNote)
        mock_client.get.assert_called_once_with("TicketNotes/1")

    @pytest.mark.asyncio
    async def test_response_without_item_key(self, manager, mock_client):
        mock_client.get.return_value = {"id": 1, "companyName": "Acme"}
        result = await manager.get(Company, 1)
        assert isinstance(result, Company)
        assert result.companyName == "Acme"

    @pytest.mark.asyncio
    async def test_string_entity_resolves_to_model(self, manager, mock_client):
        mock_client.get.return_value = {"item": {"id": 1, "title": "Test"}}
        result = await manager.get("Tickets", 1)
        assert isinstance(result, Ticket)


class TestQuery:
    @pytest.mark.asyncio
    async def test_typed(self, manager, mock_client):
        mock_client.query_all.return_value = [
            {"id": 1, "title": "T1", "status": 8},
            {"id": 2, "title": "T2", "status": 8},
        ]
        results = await manager.query(Ticket, Q(status=8))
        assert len(results) == 2
        assert all(isinstance(r, Ticket) for r in results)
        mock_client.query_all.assert_called_once_with(
            "Tickets",
            [{"field": "status", "op": "eq", "value": 8}],
            max_records=None,
        )

    @pytest.mark.asyncio
    async def test_generic(self, manager, mock_client):
        mock_client.query_all.return_value = [{"id": 1}]
        results = await manager.query("SomeEntity", Q(isActive=True))
        assert isinstance(results[0], dict)

    @pytest.mark.asyncio
    async def test_multiple_filters(self, manager, mock_client):
        mock_client.query_all.return_value = []
        await manager.query(Ticket, Q(status=8), Q(priority=4))
        filters = mock_client.query_all.call_args[0][1]
        assert len(filters) == 2

    @pytest.mark.asyncio
    async def test_child_entity(self, manager, mock_client):
        mock_client.query_all.return_value = [{"id": 1, "projectID": 100}]
        await manager.query(ProjectNote, Q(noteType=5), parent_id=100)
        mock_client.query_all.assert_called_once_with(
            "Projects/100/Notes",
            [{"field": "noteType", "op": "eq", "value": 5}],
            max_records=None,
        )

    @pytest.mark.asyncio
    async def test_max_records(self, manager, mock_client):
        mock_client.query_all.return_value = [{"id": 1}]
        await manager.query(Ticket, Q(status=1), max_records=10)
        mock_client.query_all.assert_called_once_with(
            "Tickets",
            [{"field": "status", "op": "eq", "value": 1}],
            max_records=10,
        )

    @pytest.mark.asyncio
    async def test_no_filters(self, manager, mock_client):
        mock_client.query_all.return_value = []
        await manager.query("SomeEntity")
        mock_client.query_all.assert_called_once_with(
            "SomeEntity", [], max_records=None
        )


class TestCreate:
    @pytest.mark.asyncio
    async def test_returns_item(self, manager, mock_client):
        mock_client.post.return_value = {
            "item": {"id": 999, "title": "New", "status": 1, "companyID": 100}
        }
        ticket = Ticket(title="New", status=1, companyID=100)
        result = await manager.create(ticket)
        assert isinstance(result, Ticket)
        assert result.id == 999
        mock_client.post.assert_called_once_with(
            "Tickets", json={"title": "New", "status": 1, "companyID": 100}
        )

    @pytest.mark.asyncio
    async def test_item_id_triggers_fetch(self, manager, mock_client):
        mock_client.post.return_value = {"itemId": 999}
        mock_client.get.return_value = {
            "item": {"id": 999, "title": "New", "status": 1}
        }
        ticket = Ticket(title="New", status=1, companyID=100)
        result = await manager.create(ticket)
        assert result.id == 999
        mock_client.get.assert_called_once_with("Tickets/999")

    @pytest.mark.asyncio
    async def test_child_entity_uses_parent_from_field(self, manager, mock_client):
        mock_client.post.return_value = {
            "item": {"id": 1, "ticketID": 100, "title": "Note"}
        }
        note = TicketNote(ticketID=100, title="Note", noteType=5, publish=1)
        result = await manager.create(note)
        assert isinstance(result, TicketNote)
        mock_client.post.assert_called_once()
        call_path = mock_client.post.call_args[0][0]
        assert call_path == "Tickets/100/Notes"

    @pytest.mark.asyncio
    async def test_child_entity_explicit_parent_id(self, manager, mock_client):
        mock_client.post.return_value = {
            "item": {"id": 1, "projectID": 100, "title": "Note"}
        }
        note = ProjectNote(title="Note", noteType=5, publish=1)
        await manager.create(note, parent_id=100)
        call_path = mock_client.post.call_args[0][0]
        assert call_path == "Projects/100/Notes"

    @pytest.mark.asyncio
    async def test_child_entity_missing_parent_id_raises(self, manager):
        note = ProjectNote(title="Note", noteType=5, publish=1)
        with pytest.raises(ValueError, match="child of Projects"):
            await manager.create(note)


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update(self, manager, mock_client):
        mock_client.patch.return_value = {
            "item": {"id": 1, "title": "Updated", "status": 5}
        }
        ticket = Ticket(id=1, title="Updated", status=5)
        result = await manager.update(ticket)
        assert isinstance(result, Ticket)
        assert result.status == 5
        mock_client.patch.assert_called_once_with(
            "Tickets", json={"id": 1, "title": "Updated", "status": 5}
        )

    @pytest.mark.asyncio
    async def test_update_child_entity(self, manager, mock_client):
        mock_client.patch.return_value = {
            "item": {"id": 1, "ticketID": 100, "title": "Updated"}
        }
        note = TicketNote(id=1, ticketID=100, title="Updated", noteType=5, publish=1)
        await manager.update(note)
        call_path = mock_client.patch.call_args[0][0]
        assert call_path == "Tickets/100/Notes"


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete(self, manager, mock_client):
        mock_client.delete.return_value = {"itemId": 1}
        await manager.delete(Ticket, 1)
        mock_client.delete.assert_called_once_with("Tickets/1")

    @pytest.mark.asyncio
    async def test_delete_child_entity(self, manager, mock_client):
        mock_client.delete.return_value = {"itemId": 1}
        await manager.delete(TicketNote, 1, parent_id=100)
        mock_client.delete.assert_called_once_with("Tickets/100/Notes/1")


class TestMetadata:
    @pytest.mark.asyncio
    async def test_entity_info(self, manager, mock_client):
        mock_client.get.return_value = {"canQuery": True, "canCreate": True}
        await manager.entity_info(Ticket)
        mock_client.get.assert_called_once_with("Tickets/entityInformation")

    @pytest.mark.asyncio
    async def test_field_info(self, manager, mock_client):
        mock_client.get.return_value = {"fields": []}
        await manager.field_info("Companies")
        mock_client.get.assert_called_once_with(
            "Companies/entityInformation/fields"
        )

    @pytest.mark.asyncio
    async def test_entity_info_generic(self, manager, mock_client):
        mock_client.get.return_value = {}
        await manager.entity_info("SomeEntity")
        mock_client.get.assert_called_once_with("SomeEntity/entityInformation")


class TestResolvePicklist:
    @pytest.mark.asyncio
    async def test_returns_id_label_mapping(self, manager, mock_client):
        mock_client.get.return_value = {
            "fields": [
                {
                    "name": "status",
                    "picklistValues": [
                        {"value": "1", "label": "New"},
                        {"value": "5", "label": "Complete"},
                        {"value": "8", "label": "In Progress"},
                    ],
                },
                {"name": "title"},
            ]
        }
        result = await manager.resolve_picklist(Ticket, "status")
        assert result == {1: "New", 5: "Complete", 8: "In Progress"}

    @pytest.mark.asyncio
    async def test_field_not_found_returns_empty(self, manager, mock_client):
        mock_client.get.return_value = {"fields": [{"name": "title"}]}
        result = await manager.resolve_picklist(Ticket, "nonexistent")
        assert result == {}

    @pytest.mark.asyncio
    async def test_field_with_no_picklist_values(self, manager, mock_client):
        mock_client.get.return_value = {"fields": [{"name": "status"}]}
        result = await manager.resolve_picklist(Ticket, "status")
        assert result == {}

    @pytest.mark.asyncio
    async def test_skips_entries_with_null_value(self, manager, mock_client):
        mock_client.get.return_value = {
            "fields": [
                {
                    "name": "priority",
                    "picklistValues": [
                        {"value": "1", "label": "Critical"},
                        {"value": None, "label": "Unknown"},
                        {"value": "3", "label": "Low"},
                    ],
                }
            ]
        }
        result = await manager.resolve_picklist(Ticket, "priority")
        assert result == {1: "Critical", 3: "Low"}


class TestWhoami:
    @pytest.mark.asyncio
    async def test_returns_resource_for_authenticated_user(self, manager, mock_client):
        mock_client.username = "test@example.com"
        mock_client.query_all.return_value = [
            {"id": 123, "firstName": "Test", "lastName": "User", "email": "test@example.com"}
        ]
        result = await manager.whoami()
        assert isinstance(result, Resource)
        assert result.id == 123
        assert result.firstName == "Test"

    @pytest.mark.asyncio
    async def test_raises_when_no_resource_found(self, manager, mock_client):
        mock_client.username = "unknown@example.com"
        mock_client.query_all.return_value = []
        from autotask.exceptions import AutotaskNotFoundError

        with pytest.raises(AutotaskNotFoundError, match="No resource found"):
            await manager.whoami()
