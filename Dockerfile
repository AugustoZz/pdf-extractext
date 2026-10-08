FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

# Establecer directorio de trabajo
WORKDIR /app

# Configurar variables de entorno de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# El entorno queda fuera de /app: el bind mount de Compose no lo oculta.
# uv.lock asegura las mismas versiones tanto localmente como en Docker.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copiar el resto del código
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando por defecto para iniciar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
