FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY ai_chat/requirements.txt /app/ai_chat/requirements.txt
RUN pip install --no-cache-dir -r ai_chat/requirements.txt

# Копирование кода сервиса
COPY ai_chat/ /app/ai_chat/

# Порт сервиса
EXPOSE 9001

# Команда запуска
CMD ["python", "-m", "uvicorn", "ai_chat.app.service:app", "--host", "0.0.0.0", "--port", "9001"]

