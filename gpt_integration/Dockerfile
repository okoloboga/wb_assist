FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (SSL certs, Postgres client for psycopg2, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install service requirements
COPY ./gpt_integration/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy gpt_integration code and required utils
COPY ./gpt_integration /app/gpt_integration
COPY ./bot/utils /app/utils

ENV GPT_PORT=9000
CMD ["python", "-m", "gpt_integration.service"]