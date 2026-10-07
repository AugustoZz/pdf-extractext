"""
API HTTP del extractor-service (contrato: docs/extractor_contract.md).

Versión base, sin optimizar: la extracción corre dentro del event loop, así que
mientras se procesa un PDF la réplica no atiende otras peticiones (ver #27).
"""
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request

from extractor_service.config import settings
from extractor_service.pdf_extractor import PDFValidationError, extract

app = FastAPI(title="extractor-service")


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
    data = await _read_body(request)
    try:
        return asdict(extract(data))
    except PDFValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
