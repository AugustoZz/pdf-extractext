"""
Endpoint de extracción de texto desde PDF.

POST /api/v1/extract → JSON con texto, metadatos, checksum y páginas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.infrastructure.database.repository import DocumentRepository
from app.services.extractor import PDFExtractorService, PDFValidationError

router = APIRouter()
_service = PDFExtractorService(max_file_size_mb=settings.MAX_FILE_SIZE_MB)

# No se incluye el nombre del archivo: es un dato que elige quien sube el PDF
# y no tiene sentido devolverlo tal cual en un mensaje de error.
_DUPLICATE_DETAIL = "El documento ya existe en la base de datos (checksum duplicado)."


# Tipos que usan los clientes que no declaran un MIME real (curl, algunos SDK).
# No se rechazan: la validación que vale es la firma %PDF del contenido.
_GENERIC_MIME_TYPES = frozenset({"", "application/octet-stream", "binary/octet-stream"})


def _validate_upload(file: UploadFile) -> None:
    """Valida la extensión y, si el cliente lo declara, el content-type."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .pdf")

    declared_type = (file.content_type or "").lower()
    if (
        declared_type not in _GENERIC_MIME_TYPES
        and declared_type != settings.PDF_ALLOWED_MIME_TYPE
    ):
        raise HTTPException(
            status_code=415,
            detail=f"El content-type declarado debe ser {settings.PDF_ALLOWED_MIME_TYPE}.",
        )


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

    # 2. Verificar duplicado en la BD (atajo: evita extraer texto en vano).
    #    La garantía real la da el índice único sobre 'checksum'; ver paso 4.
    existing_doc = await DocumentRepository.get_by_checksum(checksum)
    if existing_doc:
        raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL)

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

    try:
        saved_doc = await DocumentRepository.create(data_to_insert)
    except DuplicateKeyError as exc:
        # Otra petición insertó el mismo PDF entre el paso 2 y este insert.
        raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL) from exc

    return JSONResponse(status_code=201, content=saved_doc)
