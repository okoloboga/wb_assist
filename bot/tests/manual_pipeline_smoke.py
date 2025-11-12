import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к корню проекта, чтобы видеть gpt_integration
sys.path.insert(0, str(Path(__file__).parents[2]))

# Загружаем переменные окружения из корневого .env файла
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env")

from gpt_integration.analysis.pipeline import compose_messages, run_analysis


def _sample_data():
    return {
        "sales": {"revenue": 100000, "orders": 450, "avg_check": 222.22},
        "ads": {"spend": 25000, "cpc": 12.3, "roas": 4.0},
        "inventory": {"critical": 12, "ok": 380},
        "reviews": {"new": 24, "negative": 3, "rating": 4.7},
        "prices": {"avg": 1499, "discounts": 0.12},
        "competitors": {"count": 8, "median_price": 1599},
    }


class FakeClient:
    """Простой мок GPT‑клиента, возвращает текст с JSON и секцией для Telegram."""

    def complete_messages(self, messages):
        return (
            "OUTPUT_JSON:\n"
            '{"summary":"Рост ROAS и стабильные продажи",'
            '"recommendations":[{"action":"Увеличить бюджет в прибыльных кампаниях","priority":"P1","expected_effect":"+10% выручки"}],'
            '"warnings":[]}'
            "\n\nOUTPUT_TG:\n"
            "Ключевые выводы:\n"
            "- ROAS = 4.0, продажи стабильны.\n"
            "Рекомендации:\n"
            "- Увеличить бюджет в прибыльных кампаниях.\n"
        )


def main():
    data = _sample_data()

    # Соберём сообщения для LLM
    msgs = compose_messages(data)
    print(f"Messages prepared: {len(msgs)}; roles: {[m['role'] for m in msgs]}")

    # Запустим анализ с фейковым клиентом
    result = run_analysis(FakeClient(), data)

    print("\n=== JSON ===")
    print(result["json"])  # словарь

    print("\n=== Telegram chunks ===")
    chunks = result["telegram"]["chunks"]
    print(len(chunks))
    for i, ch in enumerate(chunks, 1):
        print(f"[chunk {i}] {ch[:120]}...")

    print("\n=== Sheets rows ===")
    print(len(result["sheets"]["rows"]))


if __name__ == "__main__":
    main()