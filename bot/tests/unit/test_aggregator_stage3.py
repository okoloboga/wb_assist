from typing import Any, Dict

from gpt_integration.aggregator import aggregate, build_from_sources


def test_aggregate_includes_known_keys_and_extra():
    sources: Dict[str, Any] = {
        "meta": {"shop": "X"},
        "sales": {"revenue": 100},
        "ads": {"spend": 10},
        "custom": {"foo": "bar"},
    }
    data = aggregate(sources)
    # known keys present
    assert "meta" in data and "sales" in data and "ads" in data
    # unknown keys go to extra
    assert "extra" in data and "custom" in data["extra"]


def test_build_from_sources_populates_lists_and_extra():
    data = build_from_sources(
        meta={"shop": "Y"},
        sales={"revenue": 200},
        top_products=[{"id": "SKU-1"}],
        slow_products=None,
        foo="bar",
    )
    assert data["top_products"] == [{"id": "SKU-1"}]
    # slow_products defaults to []
    assert isinstance(data["slow_products"], list) and data["slow_products"] == []
    assert "extra" in data and data["extra"]["foo"] == "bar"