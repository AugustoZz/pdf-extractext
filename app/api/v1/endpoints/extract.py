"""
Endpoint de extracción de texto desde PDF.

POST /api/v1/extract → JSON con texto, metadatos, checksum y páginas.
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.services.extractor import PDFExtractorService, PDFValidationError

from app.infrastructure.database.repository import DocumentRepository
from datetime import datetime, timezone

router = APIRouter()
_service = PDFExtractorService(max_file_size_mb=10)


def _validate_upload(file: UploadFile) -> None:
    """Valida que el archivo subido tenga extensión .pdf."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .pdf")


@router.post(
    "/extract",
    summary="Extraer texto de un PDF y guardar en BD",
    response_description="Texto extraído, metadatos y checksum del PDF.",
)
async def extract_pdf(file: UploadFile = File(..., description="Archivo PDF a procesar")):
    """
    Recibe un archivo PDF, comprueba que no exista duplicado (por checksum),
    lo procesa en memoria y lo persiste en la BD retornando en JSON:
    - **id**: ID asignado en BD.
    - **text**: texto limpio extraído de todas las páginas.
    - **page_count**: número de páginas.
    - **checksum**: hash SHA-256 del archivo original.
    - **metadata**: metadatos del PDF.
    """
    _validate_upload(file)
    file_bytes = await file.read()
    
    # 1. Calcular el checksum antes de extraer para evitar proceso innecesario si ya existe
    checksum = _service.calculate_checksum(file_bytes)
    
    # 2. Verificar duplicado en la BD
    existing_doc = await DocumentRepository.get_by_checksum(checksum)
    if existing_doc:
        raise HTTPException(
            status_code=409, 
            detail=f"El documento '{file.filename}' ya existe en la base de datos (Checksum duplicado)."
        )

    # 3. Procesar y extraer texto
    try:
        doc = _service.extract(file_bytes)
    except PDFValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 4. Guardar en Base de Datos
    data_to_insert = {
        "filename": file.filename,
        "page_count": doc.page_count,
        "checksum": doc.checksum,
        "metadata": doc.metadata,
        "text": doc.text,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    saved_doc = await DocumentRepository.create(data_to_insert)

    return JSONResponse(status_code=201, content=saved_doc)
