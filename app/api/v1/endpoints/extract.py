"""
Endpoint de extracción de texto desde PDF.

POST /api/v1/extract → JSON con texto, metadatos, checksum y páginas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.config import settings
from app.infrastructure.database.repository import DocumentRepository
from app.services.extractor import PDFValidationError, PDFTooLargeError
from app.services.extractor.http_extractor import HTTPPDFExtractorService, ExtractorHTTPError
from app.services.extractor.models import ExtractedDocument
from app.services.checksum import calculate_checksum

router = APIRouter()

# Ruta de compatibilidad con el contrato del TP de carga (POST /extract).
# No lleva prefijo /api/v1 y no se publica en el OpenAPI del servicio de documentos.
compat_router = APIRouter()
_service = HTTPPDFExtractorService(
    url=settings.EXTRACTOR_URL,
    timeout_seconds=settings.EXTRACTOR_TIMEOUT_SECONDS,
    max_file_size_mb=settings.MAX_FILE_SIZE_MB,
)

# No se incluye el nombre del archivo: es un dato que elige quien sube el PDF
# y no tiene sentido devolverlo tal cual en un mensaje de error.
_DUPLICATE_DETAIL = "El documento ya existe en la base de datos (checksum duplicado)."

# Tamaño máximo en bytes (para validar antes de hashear).
_MAX_FILE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024

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


async def _extract_document(file_bytes: bytes, *, with_metadata: bool = True) -> ExtractedDocument:
    """Extrae el documento y traduce los fallos del extractor a códigos HTTP."""
    try:
        return await _service.extract(file_bytes, with_metadata=with_metadata)
    except PDFTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except PDFValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ExtractorHTTPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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
    # Nunca leer sin límite: alcanza con un byte extra para detectar exceso.
    # UploadFile puede representar una entrada mucho mayor que nuestra RAM.
    file_bytes = await file.read(_MAX_FILE_BYTES + 1)

    # 1. Validar tamaño ANTES de hashear: si el archivo es demasiado grande,
    #    no tiene sentido calcular el checksum ni ocupar más memoria.
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo supera el tamaño máximo de {settings.MAX_FILE_SIZE_MB} MB.",
        )

    # 2. Calcular el checksum antes de extraer para evitar proceso innecesario si ya existe
    checksum = calculate_checksum(file_bytes)

    # 3. Verificar duplicado en la BD (atajo: evita extraer texto en vano).
    #    La garantía real la da el índice único sobre 'checksum'; ver paso 5.
    existing_doc = await DocumentRepository.get_by_checksum(checksum)
    if existing_doc:
        raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL)

    # 4. Procesar y extraer texto
    doc = await _extract_document(file_bytes)

    # 5. Guardar en Base de Datos
    data_to_insert = {
        "filename": file.filename,
        "page_count": doc.page_count,
        "checksum": checksum,
        "metadata": doc.metadata,
        "text": doc.text,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        saved_doc = await DocumentRepository.create(data_to_insert)
    except DuplicateKeyError as exc:
        # Otra petición insertó el mismo PDF entre el paso 3 y este insert.
        raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL) from exc

    return JSONResponse(status_code=201, content=saved_doc)


async def _read_bounded_body(request: Request, limit: int) -> bytes:
    """Lee el body binario sin cargar en memoria más de ``limit`` bytes."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_FILE_SIZE_MB} MB.",
            )
        body += chunk
    return bytes(body)


@compat_router.post(
    "/extract",
    include_in_schema=False,
    summary="Contrato del TP: PDF binario → {content, page_count}",
)
async def extract_compat(request: Request):
    """
    Alias compatible con el contrato del TP de carga y estrés.

    Acepta el PDF como body binario (``Content-Type: application/pdf``), igual
    que los scripts de k6 y Vegeta de la cátedra, o como ``multipart/form-data``
    con el campo ``file``. Responde 200 con ``{content, page_count}`` y no
    persiste nada: la extracción con CRUD sigue en ``/api/v1/extract``.
    """
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, StarletteUploadFile):
            raise HTTPException(
                status_code=400,
                detail="Falta el campo 'file' con el PDF.",
            )
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="El archivo debe tener extensión .pdf",
            )
        file_bytes = await upload.read(_MAX_FILE_BYTES + 1)
        if len(file_bytes) > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_FILE_SIZE_MB} MB.",
            )
    else:
        # Body binario directo: es el formato de los scripts de la cátedra.
        file_bytes = await _read_bounded_body(request, _MAX_FILE_BYTES)

    # El alias no devuelve metadatos: no se relee el PDF con pypdf.
    doc = await _extract_document(file_bytes, with_metadata=False)
    return {"content": doc.text, "page_count": doc.page_count}

