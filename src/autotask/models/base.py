"""Base model for all Autotask entities."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

_MODEL_REGISTRY: dict[str, type[AutotaskModel]] = {}


class AutotaskModel(BaseModel):
    """Base for all Autotask entity models.

    Subclasses set _entity_type to register with the model registry.
    Uses extra='allow' so unmodeled fields from API responses are preserved
    (important for round-tripping: read -> modify -> save).
    """

    model_config = ConfigDict(extra="allow")

    id: int | None = None

    _entity_type: ClassVar[str] = ""
    _parent_entity: ClassVar[str | None] = None
    _parent_id_field: ClassVar[str | None] = None
    _child_path: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls._entity_type:
            _MODEL_REGISTRY[cls._entity_type] = cls

    def for_create(self) -> dict[str, Any]:
        """Serialize for POST — excludes id and None fields."""
        return self.model_dump(mode="json", exclude_none=True, exclude={"id"})

    def for_update(self) -> dict[str, Any]:
        """Serialize for PATCH — includes id, excludes None fields."""
        if self.id is None:
            raise ValueError("Cannot update entity without id")
        return self.model_dump(mode="json", exclude_none=True)


def get_model_class(entity_type: str) -> type[AutotaskModel] | None:
    """Look up the model class for an entity type name."""
    return _MODEL_REGISTRY.get(entity_type)
