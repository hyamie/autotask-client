"""Tests for CLI wrapper."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from autotask.cli import cli
from autotask.models import Company, Resource, Task, TaskNote, Ticket, TicketNote


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def env_vars() -> dict[str, str]:
    return {
        "AUTOTASK_USERNAME": "test@example.com",
        "AUTOTASK_SECRET": "fake-secret",
        "AUTOTASK_INTEGRATION_CODE": "FAKE_CODE",
        "AUTOTASK_API_URL": "https://webservices24.autotask.net",
    }


@pytest.fixture
def mock_manager():
    """Patch _with_client to bypass HTTP entirely — just invoke the callback with a mock manager."""
    manager = AsyncMock()

    async def fake_with_client(callback):
        return await callback(manager)

    with patch("autotask.cli._with_client", side_effect=fake_with_client):
        yield manager


# ── Config command ──────────────────────────────────────────────


class TestConfigCommand:
    def test_config_shows_status(self, runner: CliRunner, env_vars: dict[str, str]) -> None:
        result = runner.invoke(cli, ["config"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["username"] == "test@example.com"
        assert data["has_secret"] is True
        assert data["has_integration_code"] is True

    def test_config_missing_vars(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["config"], env={})
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "error" in data


# ── Tickets ─────────────────────────────────────────────────────


class TestTicketCommands:
    def test_tickets_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Ticket(id=1, title="Test ticket", status=1),
            Ticket(id=2, title="Another ticket", status=8),
        ]
        result = runner.invoke(cli, ["tickets", "list"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["title"] == "Test ticket"

    def test_tickets_list_with_filters(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(
            cli, ["tickets", "list", "--status", "8", "--queue", "123"], env=env_vars
        )
        assert result.exit_code == 0
        # Verify the Q filters were passed — check the call args
        call_args = mock_manager.query.call_args
        assert call_args is not None

    def test_tickets_list_table_output(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Ticket(id=1, title="Test ticket", status=1),
        ]
        result = runner.invoke(cli, ["--table", "tickets", "list"], env=env_vars)
        assert result.exit_code == 0
        assert "Test ticket" in result.output
        assert "(1 records)" in result.output

    def test_tickets_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = Ticket(id=42, title="Got it", status=8)
        result = runner.invoke(cli, ["tickets", "get", "42"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 42
        assert data["title"] == "Got it"

    def test_tickets_create(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.create.return_value = Ticket(id=99, title="New ticket", status=1)
        result = runner.invoke(
            cli,
            ["tickets", "create", "--title", "New ticket", "--company-id", "100"],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 99
        # Verify create was called with a Ticket model
        created_entity = mock_manager.create.call_args[0][0]
        assert isinstance(created_entity, Ticket)
        assert created_entity.title == "New ticket"
        assert created_entity.companyID == 100

    def test_tickets_update(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.update.return_value = Ticket(id=42, title="Updated", status=5)
        result = runner.invoke(
            cli, ["tickets", "update", "42", "--status", "5"], env=env_vars
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == 5
        updated_entity = mock_manager.update.call_args[0][0]
        assert isinstance(updated_entity, Ticket)
        assert updated_entity.id == 42
        assert updated_entity.status == 5


# ── Companies ───────────────────────────────────────────────────


class TestCompanyCommands:
    def test_companies_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Company(id=1, companyName="Acme Corp", isActive=True),
        ]
        result = runner.invoke(cli, ["companies", "list"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["companyName"] == "Acme Corp"

    def test_companies_search(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(
            cli, ["companies", "list", "--search", "Acme"], env=env_vars
        )
        assert result.exit_code == 0

    def test_companies_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = Company(id=10, companyName="Test Co")
        result = runner.invoke(cli, ["companies", "get", "10"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["companyName"] == "Test Co"


# ── Resources ───────────────────────────────────────────────────


class TestResourceCommands:
    def test_resources_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Resource(id=1, firstName="John", lastName="Doe", isActive=True),
        ]
        result = runner.invoke(cli, ["resources", "list"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["firstName"] == "John"

    def test_resources_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = Resource(id=5, firstName="Jane", lastName="Smith")
        result = runner.invoke(cli, ["resources", "get", "5"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["firstName"] == "Jane"


# ── Generic query ───────────────────────────────────────────────


class TestGenericQuery:
    def test_query_known_entity(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Ticket(id=1, title="Via generic", status=1),
        ]
        result = runner.invoke(cli, ["query", "Tickets", "status=1"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["title"] == "Via generic"

    def test_query_unknown_entity(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [{"id": 1, "name": "Item"}]
        result = runner.invoke(
            cli, ["query", "ConfigurationItems", "isActive=true"], env=env_vars
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["name"] == "Item"


# ── Tasks ──────────────────────────────────────────────────────


class TestTaskCommands:
    def test_tasks_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            Task(id=1, title="Do stuff", projectID=100, status=1),
        ]
        result = runner.invoke(cli, ["tasks", "list", "--project", "100"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["title"] == "Do stuff"

    def test_tasks_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = Task(id=42, title="My task", projectID=100)
        result = runner.invoke(cli, ["tasks", "get", "42"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 42

    def test_tasks_create(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.create.return_value = Task(id=99, title="New task", projectID=100, status=1)
        result = runner.invoke(
            cli,
            ["tasks", "create", "--project-id", "100", "--title", "New task"],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 99
        created = mock_manager.create.call_args[0][0]
        assert isinstance(created, Task)
        assert created.projectID == 100

    def test_tasks_update(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.update.return_value = Task(id=42, title="Updated", projectID=100, status=5)
        result = runner.invoke(
            cli, ["tasks", "update", "42", "--status", "5"], env=env_vars
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == 5

    def test_tasks_delete(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.delete.return_value = None
        result = runner.invoke(cli, ["tasks", "delete", "42"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "deleted"


# ── Ticket Notes ───────────────────────────────────────────────


class TestTicketNoteCommands:
    def test_ticket_notes_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            TicketNote(id=1, ticketID=100, title="Note 1"),
        ]
        result = runner.invoke(cli, ["ticket-notes", "list", "100"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["title"] == "Note 1"

    def test_ticket_notes_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = TicketNote(id=5, ticketID=100, title="Got it")
        result = runner.invoke(cli, ["ticket-notes", "get", "100", "5"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 5

    def test_ticket_notes_create(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.create.return_value = TicketNote(
            id=10, ticketID=100, title="New note", description="Body"
        )
        result = runner.invoke(
            cli,
            ["ticket-notes", "create", "100", "--title", "New note", "--description", "Body"],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "New note"


# ── Task Notes ─────────────────────────────────────────────────


class TestTaskNoteCommands:
    def test_task_notes_list(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = [
            TaskNote(id=1, taskID=50, title="Progress"),
        ]
        result = runner.invoke(cli, ["task-notes", "list", "50"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["title"] == "Progress"

    def test_task_notes_create(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.create.return_value = TaskNote(
            id=10, taskID=50, title="Done", description="Finished"
        )
        result = runner.invoke(
            cli,
            ["task-notes", "create", "50", "--title", "Done", "--description", "Finished"],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["title"] == "Done"


# ── Generic CRUD ───────────────────────────────────────────────


class TestGenericCRUD:
    def test_generic_get(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.get.return_value = Ticket(id=42, title="Test", status=1)
        result = runner.invoke(cli, ["get", "Tickets", "42"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 42

    def test_generic_create(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.create.return_value = Ticket(id=99, title="New", status=1)
        result = runner.invoke(
            cli,
            ["create", "Tickets", "--fields", '{"title":"New","status":1,"companyID":100}'],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 99

    def test_generic_update(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.update.return_value = Ticket(id=42, title="T", status=5)
        result = runner.invoke(
            cli,
            ["update", "Tickets", "42", "--fields", '{"status":5}'],
            env=env_vars,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == 5

    def test_generic_delete(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.delete.return_value = None
        result = runner.invoke(cli, ["delete", "Tickets", "42"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "deleted"

    def test_generic_create_unknown_entity_fails(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        result = runner.invoke(
            cli,
            ["create", "UnknownEntity", "--fields", '{"name":"Test"}'],
            env=env_vars,
        )
        assert result.exit_code == 1


# ── Whoami ─────────────────────────────────────────────────────


class TestWhoamiCommand:
    def test_whoami(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.whoami.return_value = Resource(
            id=123, firstName="Test", lastName="User", email="test@example.com"
        )
        result = runner.invoke(cli, ["whoami"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["firstName"] == "Test"


# ── Picklist ───────────────────────────────────────────────────


class TestPicklistCommand:
    def test_picklist(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.resolve_picklist.return_value = {1: "New", 5: "Complete", 8: "In Progress"}
        result = runner.invoke(cli, ["picklist", "Tickets", "status"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["1"] == "New"


# ── Entity info ─────────────────────────────────────────────────


class TestEntityInfo:
    def test_info_command(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.entity_info.return_value = {
            "fields": [],
            "canCreate": True,
            "canQuery": True,
        }
        result = runner.invoke(cli, ["info", "Tickets"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["canCreate"] is True

    def test_fields_command(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.field_info.return_value = {
            "fields": [{"name": "title", "type": "string", "isRequired": True}],
        }
        result = runner.invoke(cli, ["fields", "Tickets"], env=env_vars)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["fields"][0]["name"] == "title"


# ── Filter parsing ──────────────────────────────────────────────


class TestFilterParsing:
    def test_int_filter(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(cli, ["query", "Tickets", "status=8"], env=env_vars)
        assert result.exit_code == 0
        # Check that the Q filter was parsed with int value
        call_args = mock_manager.query.call_args
        q_filter = call_args[0][1]  # First Q arg after entity_type
        filters = q_filter.to_filter()
        assert filters[0]["value"] == 8

    def test_bool_filter(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(cli, ["query", "Companies", "isActive=true"], env=env_vars)
        assert result.exit_code == 0

    def test_operator_filter(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(cli, ["query", "Tickets", "id__gt=100"], env=env_vars)
        assert result.exit_code == 0
        call_args = mock_manager.query.call_args
        q_filter = call_args[0][1]
        filters = q_filter.to_filter()
        assert filters[0]["op"] == "gt"
        assert filters[0]["value"] == 100

    def test_empty_results(
        self, runner: CliRunner, env_vars: dict[str, str], mock_manager: AsyncMock
    ) -> None:
        mock_manager.query.return_value = []
        result = runner.invoke(cli, ["--table", "query", "Tickets", "status=99"], env=env_vars)
        assert result.exit_code == 0
        assert "No results." in result.output
