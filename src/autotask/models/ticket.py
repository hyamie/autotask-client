"""Ticket entity model."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class Ticket(AutotaskModel):
    _entity_type: ClassVar[str] = "Tickets"

    ticketNumber: str | None = None
    title: str | None = None
    description: str | None = None
    companyID: int | None = None
    queueID: int | None = None
    status: int | None = None
    priority: int | None = None
    assignedResourceID: int | None = None
    projectID: int | None = None
    createDate: datetime | None = None
    dueDateTime: datetime | None = None
    lastActivityDate: datetime | None = None
    source: int | None = None
