FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Install bot requirements
COPY ./bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot and gpt_integration into image
COPY ./bot /app
COPY ./gpt_integration /app/gpt_integration

CMD ["python", "__main__.py"]
