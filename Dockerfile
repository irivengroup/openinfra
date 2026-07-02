FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENINFRA_APP_HOME=/app

RUN groupadd --system openinfra \
    && useradd --system --gid openinfra --home-dir /app --shell /usr/sbin/nologin openinfra

WORKDIR /app

COPY pyproject.toml README.md LICENSE VERSION ./
COPY src ./src
COPY migrations ./migrations
COPY docs/api ./docs/api

RUN python -m pip install --upgrade pip \
    && python -m pip install '.[postgresql]' \
    && chown -R openinfra:openinfra /app

USER openinfra
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
    CMD python -c "import json, urllib.request; json.loads(urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=2).read().decode('utf-8'))['ready'] or exit(1)"

CMD ["openinfra-api", "--host", "0.0.0.0", "--port", "8080", "--backend", "postgresql"]
