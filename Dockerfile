FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the package with dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

EXPOSE 4000
