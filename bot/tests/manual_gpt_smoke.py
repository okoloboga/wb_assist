import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к корню проекта, чтобы видеть gpt_integration
sys.path.insert(0, str(Path(__file__).parents[2]))

# Загружаем переменные окружения из корневого .env файла
load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env")

from gpt_integration.gpt_client import GPTClient


def main():
    import sys
    prompt = "Привет! Ответь коротко, что смоук‑тест GPT успешен."
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    try:
        client = GPTClient()
        answer = client.complete_messages([{"role": "user", "content": prompt}])
        print("\n=== Ответ LLM ===\n")
        print(answer)
        print("\n✅ Успех: соединение и ответ получены.")
    except Exception as e:
        print("\n❌ Ошибка смоук‑теста:", repr(e))
        print("Проверьте переменные окружения OPENAI_* и интернет‑доступ.")


if __name__ == "__main__":
    main()