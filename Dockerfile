FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cu128 .

COPY . .

RUN chmod +x /app/scripts/run_migrations.sh

CMD ["bash", "/app/scripts/run_migrations.sh"]