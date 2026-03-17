"""Tests for entity models."""

from datetime import datetime, timezone

import pytest

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
    get_model_class,
)


class TestForCreate:
    def test_excludes_id_and_nones(self):
        ticket = Ticket(id=1, title="Test", status=1, companyID=100)
        data = ticket.for_create()
        assert "id" not in data
        assert data == {"title": "Test", "status": 1, "companyID": 100}

    def test_datetime_serialized_as_string(self):
        project = Project(
            projectName="Test",
            startDateTime=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        data = project.for_create()
        assert isinstance(data["startDateTime"], str)
        assert "2025-01-01" in data["startDateTime"]


class TestForUpdate:
    def test_includes_id(self):
        ticket = Ticket(id=1, title="Test", status=5)
        data = ticket.for_update()
        assert data["id"] == 1
        assert data["status"] == 5

    def test_raises_without_id(self):
        ticket = Ticket(title="Test")
        with pytest.raises(ValueError, match="Cannot update"):
            ticket.for_update()


class TestExtraFields:
    def test_preserved_on_read(self):
        ticket = Ticket.model_validate(
            {"id": 1, "title": "Test", "unknownField": "value"}
        )
        assert ticket.unknownField == "value"  # type: ignore[attr-defined]

    def test_round_trip(self):
        ticket = Ticket.model_validate(
            {"id": 1, "title": "Test", "customApiField": 42}
        )
        data = ticket.for_update()
        assert data["customApiField"] == 42


class TestModelRegistry:
    def test_all_daily_drivers_registered(self):
        assert get_model_class("Tickets") is Ticket
        assert get_model_class("Projects") is Project
        assert get_model_class("Companies") is Company
        assert get_model_class("Resources") is Resource
        assert get_model_class("Tasks") is Task
        assert get_model_class("TimeEntries") is TimeEntry
        assert get_model_class("ProjectNotes") is ProjectNote
        assert get_model_class("TaskNotes") is TaskNote
        assert get_model_class("TicketNotes") is TicketNote

    def test_unknown_returns_none(self):
        assert get_model_class("SomeRandomEntity") is None

    def test_base_not_registered(self):
        assert get_model_class("") is None


class TestChildEntityMetadata:
    def test_task(self):
        assert Task._entity_type == "Tasks"
        assert Task._parent_entity == "Projects"
        assert Task._parent_id_field == "projectID"

    def test_project_note(self):
        assert ProjectNote._entity_type == "ProjectNotes"
        assert ProjectNote._parent_entity == "Projects"
        assert ProjectNote._parent_id_field == "projectID"

    def test_task_note(self):
        assert TaskNote._entity_type == "TaskNotes"
        assert TaskNote._parent_entity == "Tasks"
        assert TaskNote._parent_id_field == "taskID"

    def test_ticket_note(self):
        assert TicketNote._entity_type == "TicketNotes"
        assert TicketNote._parent_entity == "Tickets"
        assert TicketNote._parent_id_field == "ticketID"

    def test_top_level_no_parent(self):
        assert Ticket._parent_entity is None
        assert Company._parent_entity is None
        assert Project._parent_entity is None
        assert Resource._parent_entity is None
        assert TimeEntry._parent_entity is None


class TestModelConstruction:
    def test_ticket(self):
        ticket = Ticket(
            id=123,
            ticketNumber="T20250101.0001",
            title="Server down",
            companyID=456,
            status=1,
            priority=4,
            queueID=29682833,
        )
        assert ticket.id == 123
        assert ticket.ticketNumber == "T20250101.0001"
        assert ticket.companyID == 456

    def test_company(self):
        company = Company(id=1, companyName="Acme Corp", isActive=True)
        assert company.companyName == "Acme Corp"
        assert company.isActive is True

    def test_task_with_parent(self):
        task = Task(projectID=100, title="Deploy", status=8, priority=2)
        assert task.projectID == 100

    def test_time_entry(self):
        entry = TimeEntry(
            ticketID=1, resourceID=2, hoursWorked=1.5, dateWorked=datetime(2025, 3, 15)
        )
        assert entry.hoursWorked == 1.5

    def test_note(self):
        note = ProjectNote(
            projectID=100, title="Update", description="All clear", noteType=5, publish=1
        )
        assert note.projectID == 100
        assert note.noteType == 5
