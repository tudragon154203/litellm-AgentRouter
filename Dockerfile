FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install base dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Prepare project sources for editable install
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
COPY entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir -e .

EXPOSE 4000
