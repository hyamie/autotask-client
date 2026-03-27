"""Note entity models (ProjectNote, TaskNote, TicketNote)."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class _NoteBase(AutotaskModel):
    """Shared fields for all note types."""

    title: str | None = None
    description: str | None = None
    noteType: int | None = None
    publish: int | None = None
    creatorResourceID: int | None = None
    createDateTime: datetime | None = None
    lastActivityDate: datetime | None = None


class ProjectNote(_NoteBase):
    _entity_type: ClassVar[str] = "ProjectNotes"
    _parent_entity: ClassVar[str | None] = "Projects"
    _parent_id_field: ClassVar[str | None] = "projectID"
    _child_path: ClassVar[str | None] = "Notes"

    projectID: int | None = None


class TaskNote(_NoteBase):
    _entity_type: ClassVar[str] = "TaskNotes"
    _parent_entity: ClassVar[str | None] = "Tasks"
    _parent_id_field: ClassVar[str | None] = "taskID"
    _child_path: ClassVar[str | None] = "Notes"

    taskID: int | None = None


class TicketNote(_NoteBase):
    _entity_type: ClassVar[str] = "TicketNotes"
    _parent_entity: ClassVar[str | None] = "Tickets"
    _parent_id_field: ClassVar[str | None] = "ticketID"
    _child_path: ClassVar[str | None] = "Notes"

    ticketID: int | None = None
