"""
pdf-extractext — Servidor FastAPI.

Levantar con:
    python main.py
  o directamente:
    uvicorn app.main:app --reload
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.infrastructure.database.connection import connect_to_mongo, close_mongo_connection
from app.infrastructure.database.repository import DocumentRepository

# ── Logging ───────────────────────────────────────────────────────
# El nivel sale de la configuración (12-Factor III), no hardcodeado.
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Ruta absoluta al frontend: no depende del directorio desde el que se arranque.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await DocumentRepository.ensure_indexes()
    yield
    # Shutdown
    await close_mongo_connection()

# ── Aplicación FastAPI ────────────────────────────────────────────
app = FastAPI(
    title="pdf-extractext",
    description="API para extraer texto y metadatos de archivos PDF.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: abierto en desarrollo, restringido a los orígenes declarados en
# producción. Un "*" en producción permitiría a cualquier sitio consumir la API.
if settings.is_production and settings.cors_origins == ["*"]:
    logger.warning(
        "APP_ENV=production con CORS_ALLOW_ORIGINS='*': se bloquean todos los "
        "orígenes cruzados. Declará los dominios permitidos en CORS_ALLOW_ORIGINS."
    )
    allowed_origins = []
else:
    allowed_origins = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar rutas de la API v1 en /api/v1
app.include_router(v1_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    """Verificación rápida de que el servidor está vivo, redirige a la web."""
    return RedirectResponse(url="/web/index.html")

# Montar frontend estático
app.mount("/web", StaticFiles(directory=FRONTEND_DIR), name="frontend")


# ── Punto de entrada ──────────────────────────────────────────────
def main() -> None:
    """Inicia uvicorn programáticamente (usado por root main.py)."""
    logger.info("Iniciando %s en http://localhost:%d", settings.APP_NAME, settings.PORT)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    main()
