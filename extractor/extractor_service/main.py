"""
API HTTP del extractor-service (contrato: docs/extractor_contract.md).

La extracción es CPU-bound: corre en un pool de procesos para que el event loop
siga atendiendo HTTP (health checks, rechazos rápidos) mientras se procesa.
"""
import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request

from extractor_service.admission import Admission, Saturated
from extractor_service.config import settings
from extractor_service.pdf_extractor import PDFValidationError, extract


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with ProcessPoolExecutor(max_workers=settings.WORKERS) as pool:
        app.state.pool = pool
        yield


app = FastAPI(title="extractor-service", lifespan=lifespan)
_admission = Admission(capacity=settings.WORKERS, wait_timeout=settings.QUEUE_TIMEOUT_S)


async def _read_body(request: Request) -> bytes:
    """Lee el body cortando apenas supera el límite, sin cargar el archivo completo."""
    limit = settings.max_file_bytes
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_FILE_SIZE_MB} MB.",
            )
    return bytes(body)


@app.post("/extract")
async def extract_pdf(request: Request) -> dict:
    try:
        # El lugar se toma antes de leer el body: las peticiones en espera no
        # ocupan memoria con su PDF.
        async with _admission.slot():
            data = await _read_body(request)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(request.app.state.pool, extract, data)
    except Saturated as exc:
        raise HTTPException(status_code=503, detail="Servicio saturado, reintentar.") from exc
    except PDFValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(result)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
