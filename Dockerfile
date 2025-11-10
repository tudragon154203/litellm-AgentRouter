FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Node runtime alongside Python dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies
COPY package.json package-lock.json /app/
RUN npm ci --omit=dev

# Prepare project sources for editable install
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
COPY node /app/node
COPY entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir -e .

EXPOSE 4000
