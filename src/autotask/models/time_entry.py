"""TimeEntry entity model."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class TimeEntry(AutotaskModel):
    _entity_type: ClassVar[str] = "TimeEntries"

    ticketID: int | None = None
    taskID: int | None = None
    resourceID: int | None = None
    dateWorked: datetime | None = None
    hoursWorked: float | None = None
    hoursToBill: float | None = None
    summaryNotes: str | None = None
    internalNotes: str | None = None
    roleID: int | None = None
    type: int | None = None
    billingCodeID: int | None = None
    showOnInvoice: bool | None = None
    createDateTime: datetime | None = None
    startDateTime: datetime | None = None
    endDateTime: datetime | None = None
