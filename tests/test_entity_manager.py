"""Tests for the EntityManager."""

from unittest.mock import AsyncMock

import pytest

from autotask.entities.manager import EntityManager
from autotask.models import Company, ProjectNote, Task, Ticket
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
            "item": {"id": 1, "projectID": 100, "title": "Task 1"}
        }
        result = await manager.get(Task, 1, parent_id=100)
        assert isinstance(result, Task)
        mock_client.get.assert_called_once_with("Projects/100/Tasks/1")

    @pytest.mark.asyncio
    async def test_child_missing_parent_raises(self, manager):
        with pytest.raises(ValueError, match="parent_id is required"):
            await manager.get(Task, 1)

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
            "Projects/100/ProjectNotes",
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
            "item": {"id": 1, "projectID": 100, "title": "Task"}
        }
        task = Task(projectID=100, title="Task", status=1, priority=2)
        result = await manager.create(task)
        assert isinstance(result, Task)
        mock_client.post.assert_called_once()
        call_path = mock_client.post.call_args[0][0]
        assert call_path == "Projects/100/Tasks"

    @pytest.mark.asyncio
    async def test_child_entity_explicit_parent_id(self, manager, mock_client):
        mock_client.post.return_value = {
            "item": {"id": 1, "projectID": 100, "title": "Note"}
        }
        note = ProjectNote(title="Note", noteType=5, publish=1)
        await manager.create(note, parent_id=100)
        call_path = mock_client.post.call_args[0][0]
        assert call_path == "Projects/100/ProjectNotes"


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
            "item": {"id": 1, "projectID": 100, "title": "Updated"}
        }
        task = Task(id=1, projectID=100, title="Updated", status=5, priority=2)
        await manager.update(task)
        call_path = mock_client.patch.call_args[0][0]
        assert call_path == "Projects/100/Tasks"


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete(self, manager, mock_client):
        mock_client.delete.return_value = {"itemId": 1}
        await manager.delete(Ticket, 1)
        mock_client.delete.assert_called_once_with("Tickets/1")

    @pytest.mark.asyncio
    async def test_delete_child_entity(self, manager, mock_client):
        mock_client.delete.return_value = {"itemId": 1}
        await manager.delete(Task, 1, parent_id=100)
        mock_client.delete.assert_called_once_with("Projects/100/Tasks/1")


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
