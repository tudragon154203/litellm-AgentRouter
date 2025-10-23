FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install base dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install the package in editable mode
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

EXPOSE 4000
