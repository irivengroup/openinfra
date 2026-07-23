FROM python:3.11-slim

ARG OPENINFRA_UID=10001
ARG OPENINFRA_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENINFRA_APP_HOME=/app

RUN groupadd --gid "${OPENINFRA_GID}" openinfra \
    && useradd --uid "${OPENINFRA_UID}" --gid openinfra --create-home --home-dir /app --shell /usr/sbin/nologin openinfra

WORKDIR /app

COPY pyproject.toml README.md LICENSE VERSION MANIFEST.in openinfra_build_backend.py ./
COPY src ./src
COPY installers ./installers
COPY docs ./docs
COPY web ./web
COPY scripts/validate_docker_build_context.py ./scripts/validate_docker_build_context.py

RUN python scripts/validate_docker_build_context.py --project-root . \
    && python -m pip install --upgrade "pip>=26.0" \
    && python -m pip install '.[postgresql]' \
    && chown -R openinfra:openinfra /app

USER openinfra
EXPOSE 8080 2006

CMD ["openinfra-api", "--host", "0.0.0.0", "--port", "8080", "--backend", "postgresql"]
