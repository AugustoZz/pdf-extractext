"""Cliente HTTP reutilizable para el microservicio de extracción."""
import asyncio
import logging

import httpx

from app.services.extractor.models import ExtractedDocument
from app.services.extractor.pdf_extractor import (
    PDFExtractorService,
    PDFTooLargeError,
    PDFValidationError,
)

logger = logging.getLogger(__name__)


class ExtractorHTTPError(RuntimeError):
    """Fallo del servicio externo con un código HTTP seguro para la API."""

    def __init__(self, detail: str, status_code: int = 503):
        super().__init__(detail)
        self.status_code = status_code


class HTTPPDFExtractorService:
    """Extrae Markdown por HTTP; conserva metadatos locales sin extraer texto."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float = 30.0,
        max_file_size_mb: int = 10,
        client: httpx.AsyncClient | None = None,
    ):
        self._url = url
        self._timeout = timeout_seconds
        self._max_bytes = max_file_size_mb * 1024 * 1024
        self._client = client
        self._owns_client = client is None
        self._metadata_reader = PDFExtractorService(max_file_size_mb)

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                trust_env=False,
            )

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def extract(self, file_bytes: bytes) -> ExtractedDocument:
        if len(file_bytes) > self._max_bytes:
            raise PDFTooLargeError("El archivo supera el tamaño máximo permitido.")
        if not file_bytes.startswith(b"%PDF"):
            raise PDFValidationError("El archivo no tiene la firma PDF válida (%PDF).")
        if self._client is None:
            raise ExtractorHTTPError("El cliente del extractor no está inicializado.")

        try:
            response = await self._client.post(
                self._url,
                content=file_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        except httpx.RequestError as exc:
            logger.warning("No se pudo contactar al extractor: %s", type(exc).__name__)
            raise ExtractorHTTPError("El servicio de extracción no está disponible.") from exc

        if response.status_code != 200:
            if response.status_code == 422:
                raise PDFValidationError("El PDF es inválido, está corrupto o tiene contraseña.")
            if response.status_code == 413:
                raise PDFTooLargeError("El archivo supera el tamaño máximo permitido.")
            if response.status_code == 503:
                raise ExtractorHTTPError("El servicio de extracción está saturado; intentá nuevamente.")
            raise ExtractorHTTPError("El extractor devolvió una respuesta inesperada.", 502)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExtractorHTTPError("El extractor devolvió JSON inválido.", 502) from exc
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("content"), str)
            or type(payload.get("page_count")) is not int
            or payload["page_count"] < 1
        ):
            raise ExtractorHTTPError("El extractor devolvió un resultado inválido.", 502)

        # El contrato del extractor incluye content/page_count. Leer sólo los
        # metadatos mantiene el contrato de documentos sin repetir la costosa
        # extracción de texto ni bloquear el event loop.
        metadata = await asyncio.to_thread(self._read_metadata, file_bytes)
        return ExtractedDocument(payload["content"], payload["page_count"], metadata)

    def _read_metadata(self, file_bytes: bytes) -> dict:
        try:
            return self._metadata_reader.extract_metadata(file_bytes)
        except Exception as exc:
            # Los metadatos son opcionales y no invalidan una extracción que el
            # servicio remoto ya completó correctamente.
            logger.warning("No se pudieron leer metadatos opcionales: %s", type(exc).__name__)
            return {}
