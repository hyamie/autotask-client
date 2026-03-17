"""Generic entity manager for CRUD operations.

Provides typed access when a model class is used, or raw dict access
for the ~200 entity types without hand-crafted models.
"""

from __future__ import annotations

from typing import Any

from autotask.client import AutotaskClient
from autotask.models.base import AutotaskModel, get_model_class
from autotask.query import Q


class EntityManager:
    """CRUD operations for Autotask entities.

    Usage:
        async with AutotaskClient(config) as client:
            em = EntityManager(client)

            # Typed access (returns model instances)
            tickets = await em.query(Ticket, Q(status=8))

            # Generic access (returns dicts)
            items = await em.query("SomeObscureEntity", Q(isActive=True))
    """

    def __init__(self, client: AutotaskClient) -> None:
        self._client = client

    async def get(
        self,
        entity_type: type[AutotaskModel] | str,
        entity_id: int,
        *,
        parent_id: int | None = None,
    ) -> AutotaskModel | dict[str, Any]:
        """Get a single entity by ID."""
        path = self._entity_path(entity_type, parent_id)
        result = await self._client.get(f"{path}/{entity_id}")
        item = result.get("item", result)
        model_class = self._resolve_model(entity_type)
        if model_class:
            return model_class.model_validate(item)
        return dict(item)

    async def query(
        self,
        entity_type: type[AutotaskModel] | str,
        *filters: Q,
        parent_id: int | None = None,
        max_records: int | None = None,
    ) -> list[AutotaskModel] | list[dict[str, Any]]:
        """Query entities with filters. Returns typed models or raw dicts."""
        path = self._entity_path(entity_type, parent_id)
        combined_filters: list[dict[str, Any]] = []
        for f in filters:
            combined_filters.extend(f.to_filter())
        items = await self._client.query_all(
            path, combined_filters, max_records=max_records
        )
        model_class = self._resolve_model(entity_type)
        if model_class:
            return [model_class.model_validate(item) for item in items]
        return items

    async def create(
        self,
        entity: AutotaskModel,
        *,
        parent_id: int | None = None,
    ) -> AutotaskModel:
        """Create an entity. Returns the created entity."""
        cls = type(entity)
        parent_id = parent_id or self._extract_parent_id(entity)
        path = self._entity_path(cls, parent_id)
        result = await self._client.post(path, json=entity.for_create())
        item = result.get("item")
        if item is None and "itemId" in result:
            fetched = await self.get(cls, result["itemId"], parent_id=parent_id)
            return fetched  # type: ignore[return-value]
        return cls.model_validate(item or result)

    async def update(
        self,
        entity: AutotaskModel,
        *,
        parent_id: int | None = None,
    ) -> AutotaskModel:
        """Update an entity via PATCH (partial update, safe)."""
        cls = type(entity)
        parent_id = parent_id or self._extract_parent_id(entity)
        path = self._entity_path(cls, parent_id)
        result = await self._client.patch(path, json=entity.for_update())
        item = result.get("item", result)
        return cls.model_validate(item)

    async def delete(
        self,
        entity_type: type[AutotaskModel] | str,
        entity_id: int,
        *,
        parent_id: int | None = None,
    ) -> None:
        """Delete an entity by ID."""
        path = self._entity_path(entity_type, parent_id)
        await self._client.delete(f"{path}/{entity_id}")

    async def entity_info(
        self, entity_type: type[AutotaskModel] | str
    ) -> dict[str, Any]:
        """Get entity capabilities (canCreate, canQuery, etc.)."""
        path = self._entity_path(entity_type)
        return await self._client.get(f"{path}/entityInformation")

    async def field_info(
        self, entity_type: type[AutotaskModel] | str
    ) -> dict[str, Any]:
        """Get field definitions (types, required, picklists)."""
        path = self._entity_path(entity_type)
        return await self._client.get(f"{path}/entityInformation/fields")

    def _entity_path(
        self,
        entity_type: type[AutotaskModel] | str,
        parent_id: int | None = None,
    ) -> str:
        """Build the API path for an entity type."""
        if isinstance(entity_type, type) and issubclass(entity_type, AutotaskModel):
            if entity_type._parent_entity:
                if parent_id is None:
                    raise ValueError(
                        f"{entity_type.__name__} is a child entity of "
                        f"{entity_type._parent_entity}; parent_id is required"
                    )
                return (
                    f"{entity_type._parent_entity}/{parent_id}"
                    f"/{entity_type._entity_type}"
                )
            return entity_type._entity_type
        return str(entity_type)

    def _extract_parent_id(self, entity: AutotaskModel) -> int | None:
        """Pull parent ID from the entity's parent ID field, if defined."""
        if entity._parent_id_field:
            return getattr(entity, entity._parent_id_field, None)
        return None

    def _resolve_model(
        self, entity_type: type[AutotaskModel] | str
    ) -> type[AutotaskModel] | None:
        """Resolve entity_type to a model class (or None for generic access)."""
        if isinstance(entity_type, type) and issubclass(entity_type, AutotaskModel):
            return entity_type
        if isinstance(entity_type, str):
            return get_model_class(entity_type)
        return None
