# Build context is the repository root: docker compose passes `context: .`.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Only the bot's own dependencies. asyncpg and SQLAlchemy are deliberately
# absent: the bot cannot reach the database even by accident.
COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r bot/requirements.txt

COPY bot ./bot

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /code
USER appuser

CMD ["python", "-m", "bot"]
