FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
COPY scripts ./scripts

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -e '.[production]'

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
