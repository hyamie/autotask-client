"""Tests for query filter builder DSL."""

from autotask.query import Q


def test_simple_eq() -> None:
    """Q builds an equality filter."""
    f = Q(status=1)
    assert f.to_filter() == [{"field": "status", "op": "eq", "value": 1}]


def test_operator_suffix() -> None:
    """Q supports operator suffixes like __gt, __contains."""
    f = Q(id__gt=100)
    assert f.to_filter() == [{"field": "id", "op": "gt", "value": 100}]

    f = Q(title__contains="server")
    assert f.to_filter() == [{"field": "title", "op": "contains", "value": "server"}]


def test_multiple_filters_and() -> None:
    """Multiple kwargs produce AND filters."""
    f = Q(status=1, priority=4)
    filters = f.to_filter()
    assert len(filters) == 2
    fields = {f["field"] for f in filters}
    assert fields == {"status", "priority"}


def test_in_operator() -> None:
    """Q supports __in for list values."""
    f = Q(status__in=[1, 5, 8])
    assert f.to_filter() == [{"field": "status", "op": "in", "value": [1, 5, 8]}]


def test_udf_filter() -> None:
    """Q supports UDF filters with udf=True."""
    f = Q.udf(my_custom_field="value")
    filters = f.to_filter()
    assert filters[0]["udf"] is True


def test_combine_with_and() -> None:
    """Q objects can be combined with &."""
    f = Q(status=1) & Q(priority=4)
    filters = f.to_filter()
    assert len(filters) == 2


def test_raw_filter() -> None:
    """Q.raw passes through a pre-built filter dict."""
    raw = {"field": "status", "op": "eq", "value": 1}
    f = Q.raw(raw)
    assert f.to_filter() == [raw]
