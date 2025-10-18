import os
import sys
from dotenv import load_dotenv

from gpt_client import LLMConfig, GPTClient


def main() -> int:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("[WARN] .env not found. Using system env variables.")

    try:
        config = LLMConfig.from_env()
        client = GPTClient(config)
    except Exception as e:
        print("[ERROR] Client init failed:", repr(e))
        return 1

    prompt = "Напиши 'pong'."
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    print("[INFO] Запрос:", prompt)
    try:
        answer = client.complete(prompt)
        print("[OK] Ответ:", answer)
        return 0
    except Exception as e:
        print("[ERROR] Request failed:", repr(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())