import os
from dotenv import load_dotenv

# Optional: use httpx client from OpenAI SDK
from openai import OpenAI


def main():
    # Load .env from local gpt_integration directory
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print("[WARN] .env not found. Using system env variables.")

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "200"))
    timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))
    system_prompt = os.getenv("OPENAI_SYSTEM_PROMPT", "You are WB Assist helper. Reply shortly.")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY is not set. Please create gpt_integration/.env.")
        return 1

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    print("[INFO] Sending test request to OpenAI...")

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "ping"},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = completion.choices[0].message.content
        print("[OK] Response:", (text or "<empty>").strip())
        return 0
    except Exception as e:
        print("[ERROR] Request failed:", repr(e))
        return 2


if __name__ == "__main__":
    exit_code = main()
    if exit_code != 0:
        raise SystemExit(exit_code)