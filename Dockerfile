FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
COPY --from=deps /install /usr/local
RUN useradd --create-home appuser
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
# aplica as migrations e sobe a API (PORT é definida pela plataforma)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]