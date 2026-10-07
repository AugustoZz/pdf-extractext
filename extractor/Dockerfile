FROM python:3.12-slim

# uv instala exactamente las versiones de uv.lock (12-Factor II: dependencias).
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Primero sólo las dependencias: esta capa se reutiliza mientras no cambie el lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY extractor_service ./extractor_service

EXPOSE 8000
CMD ["uvicorn", "extractor_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
