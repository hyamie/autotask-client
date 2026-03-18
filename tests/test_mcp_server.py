"""Tests for MCP server tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from autotask.models import Resource, Ticket


@pytest.fixture
def mock_manager():
    return AsyncMock()


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def patch_get_manager(mock_client, mock_manager):
    with patch(
        "autotask.mcp_server._get_manager",
        return_value=(mock_client, mock_manager),
    ):
        yield


class TestAutotaskQuery:
    @pytest.mark.asyncio
    async def test_query_returns_results(self, mock_manager):
        from autotask.mcp_server import autotask_query

        mock_manager.query.return_value = [
            Ticket(id=1, title="Test", status=8),
            Ticket(id=2, title="Other", status=1),
        ]
        result = await autotask_query("Tickets", {"status": 8}, limit=50)
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_query_invalid_entity_name(self):
        from autotask.mcp_server import autotask_query

        result = await autotask_query("'; DROP TABLE--", {})
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_query_caps_limit(self, mock_manager):
        from autotask.mcp_server import autotask_query

        mock_manager.query.return_value = []
        await autotask_query("Tickets", {}, limit=9999)
        call_kwargs = mock_manager.query.call_args[1]
        assert call_kwargs["max_records"] == 500


class TestAutotaskGet:
    @pytest.mark.asyncio
    async def test_get_returns_entity(self, mock_manager):
        from autotask.mcp_server import autotask_get

        mock_manager.get.return_value = Ticket(id=42, title="Got it", status=8)
        result = await autotask_get("Tickets", 42)
        data = json.loads(result)
        assert data["id"] == 42
        assert data["title"] == "Got it"

    @pytest.mark.asyncio
    async def test_get_invalid_entity_name(self):
        from autotask.mcp_server import autotask_get

        result = await autotask_get("123bad", 1)
        data = json.loads(result)
        assert "error" in data


class TestAutotaskCreate:
    @pytest.mark.asyncio
    async def test_create_returns_entity(self, mock_manager):
        from autotask.mcp_server import autotask_create

        mock_manager.create.return_value = Ticket(id=99, title="New", status=1)
        result = await autotask_create(
            "Tickets", {"title": "New", "status": 1, "companyID": 100}
        )
        data = json.loads(result)
        assert data["id"] == 99

    @pytest.mark.asyncio
    async def test_create_unknown_entity_returns_error(self):
        from autotask.mcp_server import autotask_create

        result = await autotask_create("UnknownEntity", {"name": "Test"})
        data = json.loads(result)
        assert "error" in data


class TestAutotaskUpdate:
    @pytest.mark.asyncio
    async def test_update_returns_entity(self, mock_manager):
        from autotask.mcp_server import autotask_update

        mock_manager.update.return_value = Ticket(id=42, title="Updated", status=5)
        result = await autotask_update("Tickets", 42, {"status": 5})
        data = json.loads(result)
        assert data["status"] == 5


class TestAutotaskDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_confirmation(self, mock_manager):
        from autotask.mcp_server import autotask_delete

        mock_manager.delete.return_value = None
        result = await autotask_delete("Tickets", 42)
        data = json.loads(result)
        assert data["status"] == "deleted"
        assert data["id"] == 42


class TestAutotaskResolvePicklist:
    @pytest.mark.asyncio
    async def test_resolve_picklist(self, mock_manager):
        from autotask.mcp_server import autotask_resolve_picklist

        mock_manager.resolve_picklist.return_value = {1: "New", 5: "Complete"}
        result = await autotask_resolve_picklist("Tickets", "status")
        data = json.loads(result)
        assert data["1"] == "New"
        assert data["5"] == "Complete"


class TestAutotaskWhoami:
    @pytest.mark.asyncio
    async def test_whoami(self, mock_manager):
        from autotask.mcp_server import autotask_whoami

        mock_manager.whoami.return_value = Resource(
            id=123, firstName="Test", lastName="User"
        )
        result = await autotask_whoami()
        data = json.loads(result)
        assert data["id"] == 123
        assert data["firstName"] == "Test"


class TestAutotaskEntityInfo:
    @pytest.mark.asyncio
    async def test_entity_info(self, mock_manager):
        from autotask.mcp_server import autotask_entity_info

        mock_manager.entity_info.return_value = {"canCreate": True, "canQuery": True}
        result = await autotask_entity_info("Tickets")
        data = json.loads(result)
        assert data["canCreate"] is True


class TestAutotaskFieldInfo:
    @pytest.mark.asyncio
    async def test_field_info(self, mock_manager):
        from autotask.mcp_server import autotask_field_info

        mock_manager.field_info.return_value = {
            "fields": [{"name": "title", "type": "string"}]
        }
        result = await autotask_field_info("Tickets")
        data = json.loads(result)
        assert data["fields"][0]["name"] == "title"


class TestMCPServerRegistration:
    @pytest.mark.asyncio
    async def test_server_has_expected_tools(self):
        from autotask.mcp_server import mcp

        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "autotask_query",
            "autotask_get",
            "autotask_create",
            "autotask_update",
            "autotask_delete",
            "autotask_entity_info",
            "autotask_field_info",
            "autotask_resolve_picklist",
            "autotask_whoami",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_server_name_and_version(self):
        from autotask.mcp_server import mcp

        assert mcp.name == "autotask"
