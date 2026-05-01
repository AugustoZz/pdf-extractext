"""
pdf-extractext — Servidor FastAPI.

Levantar con:
    python main.py
  o directamente:
    uvicorn app.main:app --reload
"""
import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.v1 import router as v1_router

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from app.infrastructure.database.connection import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
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

# Permitir peticiones desde cualquier origen (útil en desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.mount("/web", StaticFiles(directory="frontend"), name="frontend")


# ── Punto de entrada ──────────────────────────────────────────────
def main() -> None:
    """Inicia uvicorn programáticamente (usado por root main.py)."""
    logger.info("Iniciando pdf-extractext en http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
