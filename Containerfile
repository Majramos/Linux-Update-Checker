FROM docker.io/library/python:3.12-slim

ARG PKG_URL="linux-update-checker @ git+https://gitlab.com/majramos/linux-update-checker.git"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install "${PKG_URL}"

ENTRYPOINT ["linux-update-checker"]
