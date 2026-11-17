"""
Cliente HTTP reutilizable para el microservicio de extracción.

Antes de cada llamada:
1. El circuit breaker decide si se llama o se responde 503 enseguida.
2. El resolver dice a qué URL llamar (fija, o la que informa Consul).
"""
import asyncio
import logging

import httpx

from app.infrastructure.consul import NoHealthyInstanceError, ServiceResolver, StaticURLResolver
from app.services.resilience import CircuitBreaker, CircuitOpenError
from app.services.extractor.models import ExtractedDocument
from app.services.extractor.pdf_extractor import (
    PDFExtractorService,
    PDFTooLargeError,
    PDFValidationError,
)

logger = logging.getLogger(__name__)


class ExtractorHTTPError(RuntimeError):
    """Fallo del servicio externo con un código HTTP seguro para la API."""

    def __init__(self, detail: str, status_code: int = 503, retry_after: float | None = None):
        super().__init__(detail)
        self.status_code = status_code
        # Segundos sugeridos para reintentar (cabecera Retry-After), si se sabe.
        self.retry_after = retry_after


def _remote_detail(response: httpx.Response) -> str | None:
    """El ``detail`` del extractor (p. ej. "protegido con contraseña"), si vino uno."""
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return None
    return detail if isinstance(detail, str) and detail.strip() else None


class HTTPPDFExtractorService:
    """Extrae Markdown por HTTP; conserva metadatos locales sin extraer texto."""

    def __init__(
        self,
        url: str,
        timeout_seconds: float = 30.0,
        max_file_size_mb: int = 10,
        client: httpx.AsyncClient | None = None,
        *,
        resolver: ServiceResolver | None = None,
        breaker: CircuitBreaker | None = None,
    ):
        self._resolver = resolver or StaticURLResolver(url)
        self._breaker = breaker or CircuitBreaker("extractor")
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
        await self._resolver.start()

    async def close(self) -> None:
        try:
            await self._resolver.close()
        finally:
            if self._client is not None and self._owns_client:
                await self._client.aclose()
                self._client = None

    async def extract(self, file_bytes: bytes, *, with_metadata: bool = True) -> ExtractedDocument:
        """
        Envía el PDF al extractor y devuelve su Markdown.

        Con ``with_metadata=False`` no se relee el PDF con pypdf: el alias
        ``POST /extract`` descarta los metadatos y esa lectura es CPU de la API.
        """
        # Errores del cliente: no dicen nada de la salud del extractor.
        if len(file_bytes) > self._max_bytes:
            raise PDFTooLargeError("El archivo supera el tamaño máximo permitido.")
        if not file_bytes.startswith(b"%PDF"):
            raise PDFValidationError("El archivo no tiene la firma PDF válida (%PDF).")
        if self._client is None:
            raise ExtractorHTTPError("El cliente del extractor no está inicializado.")

        try:
            self._breaker.before_call()
        except CircuitOpenError as exc:
            raise ExtractorHTTPError(
                "El servicio de extracción falló varias veces seguidas; "
                "se pausan las llamadas. Intentá nuevamente en unos segundos.",
                retry_after=max(exc.retry_after, 1.0),
            ) from exc

        try:
            payload = await self._call_extractor(file_bytes)
        except (PDFValidationError, PDFTooLargeError):
            # El extractor contestó bien: el problema es el PDF.
            self._breaker.record_success()
            raise
        except asyncio.CancelledError:
            # El cliente cortó: la llamada no terminó, no es éxito ni fallo.
            self._breaker.release()
            raise
        except Exception:
            self._breaker.record_failure()
            raise
        self._breaker.record_success()

        if not with_metadata:
            return ExtractedDocument(payload["content"], payload["page_count"], {})

        # El contrato del extractor incluye content/page_count. Leer sólo los
        # metadatos mantiene el contrato de documentos sin repetir la costosa
        # extracción de texto ni bloquear el event loop.
        metadata = await asyncio.to_thread(self._read_metadata, file_bytes)
        return ExtractedDocument(payload["content"], payload["page_count"], metadata)

    async def _call_extractor(self, file_bytes: bytes) -> dict:
        """Una llamada al extractor; devuelve el JSON validado o lanza el error del contrato."""
        try:
            url = await self._resolver.resolve()
        except NoHealthyInstanceError as exc:
            logger.warning("Sin instancias del extractor: %s", exc)
            raise ExtractorHTTPError("El servicio de extracción no está disponible.") from exc

        try:
            response = await self._client.post(
                url,
                content=file_bytes,
                headers={"Content-Type": "application/pdf"},
            )
        except httpx.RequestError as exc:
            logger.warning("No se pudo contactar al extractor: %s", type(exc).__name__)
            raise ExtractorHTTPError("El servicio de extracción no está disponible.") from exc

        if response.status_code != 200:
            if response.status_code == 422:
                raise PDFValidationError(
                    _remote_detail(response)
                    or "El PDF es inválido, está corrupto o tiene contraseña."
                )
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
        return payload

    def _read_metadata(self, file_bytes: bytes) -> dict:
        try:
            return self._metadata_reader.extract_metadata(file_bytes)
        except Exception as exc:
            # Los metadatos son opcionales y no invalidan una extracción que el
            # servicio remoto ya completó correctamente.
            logger.warning("No se pudieron leer metadatos opcionales: %s", type(exc).__name__)
            return {}
