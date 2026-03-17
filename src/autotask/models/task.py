"""Task entity model."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class Task(AutotaskModel):
    _entity_type: ClassVar[str] = "Tasks"
    _parent_entity: ClassVar[str | None] = None
    _parent_id_field: ClassVar[str | None] = None

    projectID: int | None = None
    title: str | None = None
    description: str | None = None
    status: int | None = None
    priority: int | None = None
    assignedResourceID: int | None = None
    departmentID: int | None = None
    estimatedHours: float | None = None
    hoursWorked: float | None = None
    startDateTime: datetime | None = None
    endDateTime: datetime | None = None
    completedDateTime: datetime | None = None
    createDateTime: datetime | None = None
    lastActivityDateTime: datetime | None = None
    taskNumber: str | None = None
    sortOrder: int | None = None
    phaseID: int | None = None
