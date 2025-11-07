FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY bot_young/requirements.txt /app/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot_young/ /app/bot_young/

# Рабочая директория
WORKDIR /app

# Запуск бота
CMD ["python", "-m", "bot_young"]

