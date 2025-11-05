import json
from typing import Any, Dict

import pytest

from gpt_integration.analysis.pipeline import compose_messages, run_analysis


def _sample_data() -> Dict[str, Any]:
    return {
        "sales": {"revenue": 100000, "orders": 450, "avg_check": 222.22},
        "ads": {"spend": 25000, "cpc": 12.3, "roas": 4.0},
        "inventory": {"critical": 12, "ok": 380},
        "reviews": {"new": 24, "negative": 3, "rating": 4.7},
        "prices": {"avg": 1499, "discounts": 0.12},
        "competitors": {"count": 8, "median_price": 1599},
    }


class FakeClient:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload

    def complete_messages(self, messages):
        return json.dumps(self.payload, ensure_ascii=False)


def test_validation_errors_when_missing_keys():
    data = {"meta": {"shop": "X"}}
    payload = {
        "telegram": {"chunks": ["ok"]},
        "sheets": {"headers": [], "rows": []},
    }
    result = run_analysis(FakeClient(payload), data, validate=True)
    errors = result.get("validation_errors")
    assert errors and any("Missing key" in e for e in errors)


def test_validation_pass_on_minimal_structure():
    data = {"meta": {"shop": "X"}}
    payload = {
        "key_metrics": [],
        "anomalies": [],
        "insights": [],
        "recommendations": [],
        "telegram": {"chunks": ["ok"]},
        "sheets": {"headers": [], "rows": []},
    }
    result = run_analysis(FakeClient(payload), data, validate=True)
    assert result.get("validation_errors") == []


def test_compose_messages_contains_schema_and_tasks():
    msgs = compose_messages({}, template_path=None)
    assert any("OUTPUT_JSON_SCHEMA" in m["content"] for m in msgs if m["role"] == "user")


def test_compose_messages_includes_sections():
    data = _sample_data()
    msgs = compose_messages(data)
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "system" and len(msgs[0]["content"]) > 0
    assert msgs[1]["role"] == "user"
    uc = msgs[1]["content"]
    assert "## DATA" in uc
    # DATA serialized
    assert "sales" in uc and "ads" in uc and "inventory" in uc


def test_run_analysis_parses_structured_json_and_channels():
    data = _sample_data()
    payload = {
        "summary": {"kpi": {"sales": 100000, "ads_spend": 25000}},
        "telegram": {"chunks": ["*Сводка*: продажи 100000, реклама 25000"]},
        "sheets": {"headers": ["metric", "value"], "rows": [["sales", 100000], ["ads_spend", 25000]]},
    }
    client = FakeClient(payload)
    result = run_analysis(client, data)

    # raw and messages
    assert isinstance(result["raw_response"], str) and len(result["raw_response"]) > 0
    assert isinstance(result["messages"], list) and len(result["messages"]) == 2

    # parsed json
    j = result["json"]
    assert isinstance(j, dict)
    assert "summary" in j and "telegram" in j and "sheets" in j

    # telegram prepared
    tg = result["telegram"]
    assert isinstance(tg, dict)
    assert "chunks" in tg and isinstance(tg["chunks"], list)
    assert len(tg["chunks"]) >= 1
    assert "character_count" in tg and isinstance(tg["character_count"], int)

    # sheets prepared
    sh = result["sheets"]
    assert isinstance(sh, dict)
    assert "headers" in sh and isinstance(sh["headers"], list)
    assert "rows" in sh and isinstance(sh["rows"], list)