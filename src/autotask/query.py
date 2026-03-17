"""Query filter builder for Autotask API.

Provides a Django-like Q object for building filter expressions:
    Q(status=1)                    -> {"field": "status", "op": "eq", "value": 1}
    Q(id__gt=100)                  -> {"field": "id", "op": "gt", "value": 100}
    Q(title__contains="server")    -> {"field": "title", "op": "contains", "value": "server"}
    Q(status__in=[1, 5, 8])        -> {"field": "status", "op": "in", "value": [1, 5, 8]}

Supported operators: eq, noteq, gt, gte, lt, lte, beginsWith, endsWith,
contains, exist, notExist, in, notIn
"""

from __future__ import annotations

from typing import Any

VALID_OPS = frozenset({
    "eq", "noteq", "gt", "gte", "lt", "lte",
    "beginsWith", "endsWith", "contains",
    "exist", "notExist", "in", "notIn",
})

_OP_ALIASES: dict[str, str] = {
    "ne": "noteq",
    "not_eq": "noteq",
    "begins_with": "beginsWith",
    "ends_with": "endsWith",
    "not_exist": "notExist",
    "not_in": "notIn",
}


class Q:
    """Query filter builder with Django-like syntax."""

    def __init__(self, **kwargs: Any) -> None:
        self._filters: list[dict[str, Any]] = []
        for key, value in kwargs.items():
            field, op = self._parse_key(key)
            self._filters.append({"field": field, "op": op, "value": value})

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        """Parse 'field__op' into (field, op). Default op is 'eq'."""
        if "__" in key:
            field, op_raw = key.rsplit("__", 1)
            op = _OP_ALIASES.get(op_raw, op_raw)
            if op not in VALID_OPS:
                raise ValueError(f"Unknown operator: {op_raw} (resolved to {op})")
            return field, op
        return key, "eq"

    @classmethod
    def udf(cls, **kwargs: Any) -> Q:
        """Create a UDF (User Defined Field) filter.

        Only ONE UDF filter is allowed per query (Autotask limitation).
        """
        instance = cls(**kwargs)
        for f in instance._filters:
            f["udf"] = True
        return instance

    @classmethod
    def raw(cls, filter_dict: dict[str, Any]) -> Q:
        """Create a Q from a raw filter dict. Validates op against allowed operators."""
        op = filter_dict.get("op")
        if op and op not in VALID_OPS:
            raise ValueError(f"Unknown operator in raw filter: {op}")
        instance = cls()
        instance._filters = [filter_dict]
        return instance

    def __and__(self, other: Q) -> Q:
        """Combine two Q objects with AND (all filters in one list)."""
        combined = Q()
        combined._filters = self._filters + other._filters
        udf_count = sum(1 for f in combined._filters if f.get("udf"))
        if udf_count > 1:
            raise ValueError("Autotask allows only ONE UDF filter per query")
        return combined

    def to_filter(self) -> list[dict[str, Any]]:
        """Convert to the Autotask API filter format."""
        return list(self._filters)
