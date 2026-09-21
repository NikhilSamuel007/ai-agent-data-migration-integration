FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DB_PATH=/app/data/relay-v3.sqlite \
    MODEL_CACHE_DIR=/app/.cache/models \
    HF_HOME=/app/.cache/huggingface
WORKDIR /app/backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
RUN groupadd --gid 10001 relay \
    && useradd --uid 10001 --gid relay --create-home relay \
    && mkdir -p /app/data /app/.cache \
    && chown -R relay:relay /app
COPY --chown=relay:relay server.py schema.json ./
COPY --chown=relay:relay relay/ ./relay/
COPY --chown=relay:relay samples/ ./samples/
USER relay
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=3).close()"
CMD ["python", "server.py"]
