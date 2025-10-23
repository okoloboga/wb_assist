FROM python:3.12-slim

WORKDIR /app

# Install bot requirements
COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot and gpt_integration into image
COPY . /app

CMD ["python", "__main__.py"]
