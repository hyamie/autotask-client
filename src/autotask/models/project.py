"""Project entity model."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class Project(AutotaskModel):
    _entity_type: ClassVar[str] = "Projects"

    projectNumber: str | None = None
    projectName: str | None = None
    companyID: int | None = None
    projectType: int | None = None
    status: int | None = None
    startDateTime: datetime | None = None
    endDateTime: datetime | None = None
    projectLeadResourceID: int | None = None
    description: str | None = None
    organizationalLevelAssociationID: int | None = None
    completedPercentage: int | None = None
    completedDateTime: datetime | None = None
    statusDetail: str | None = None
