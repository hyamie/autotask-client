"""Resource (user/technician) entity model."""

from __future__ import annotations

from typing import ClassVar

from autotask.models.base import AutotaskModel


class Resource(AutotaskModel):
    _entity_type: ClassVar[str] = "Resources"

    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    isActive: bool | None = None
    resourceType: str | None = None
    title: str | None = None
