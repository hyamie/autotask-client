"""Company entity model."""

from __future__ import annotations

from typing import ClassVar

from autotask.models.base import AutotaskModel


class Company(AutotaskModel):
    _entity_type: ClassVar[str] = "Companies"

    companyName: str | None = None
    companyNumber: str | None = None
    companyType: int | None = None
    phone: str | None = None
    isActive: bool | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    state: str | None = None
    postalCode: str | None = None
    country: str | None = None
    ownerResourceID: int | None = None
