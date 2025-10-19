import json
from typing import Any, Dict

from gpt_integration.pipeline import compose_messages, run_analysis


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
    def complete_messages(self, messages):
        # Ensure messages contain SYSTEM and DATA
        assert isinstance(messages, list) and len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user" and "## DATA" in messages[1]["content"]
        # Return structured JSON and OUTPUT_TG fallback text
        return (
            "OUTPUT_JSON:\n"
            + json.dumps(
                {
                    "summary": {
                        "kpi": {"sales": 100000, "ads_spend": 25000},
                        "insights": [
                            {"title": "Рост продаж", "reason": "Снижение цены"}
                        ],
                    },
                    "recommendations": [
                        {"action": "Увеличить ставку", "priority": "P1"}
                    ],
                    "telegram": {
                        "chunks": [
                            "*Сводка*: продажи 100000, реклама 25000",
                            "Аномалии: снижение цены, рост конверсии",
                        ]
                    },
                    "sheets": {
                        "headers": ["metric", "value"],
                        "rows": [["sales", 100000], ["ads_spend", 25000]],
                    },
                },
                ensure_ascii=False,
            )
            + "\nOUTPUT_TG:\n*Сводка*: продажи 100000, реклама 25000\n"
        )


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
    client = FakeClient()
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