"""
Servicio de extracción de texto desde archivos PDF.

Principio SRP: esta clase SOLO se encarga de procesar PDFs.
No persiste datos, no genera resúmenes ni interactúa con la API.
"""
import hashlib
import io
import logging

import pypdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.extractor.models import ExtractedDocument

logger = logging.getLogger(__name__)


class PDFValidationError(ValueError):
    """Se lanza cuando el archivo no es un PDF válido o supera el tamaño máximo."""


class PDFExtractorService:
    """
    Servicio responsable de:
      1. Validar el PDF (formato y tamaño).
      2. Extraer texto de todas las páginas.
      3. Extraer metadatos del PDF.
      4. Calcular el checksum SHA-256.

    Uso:
        service = PDFExtractorService(max_file_size_mb=10)
        doc = service.extract(file_bytes)
    """

    def __init__(self, max_file_size_mb: int = 10) -> None:
        self._max_bytes = max_file_size_mb * 1024 * 1024

    # ── Método principal ──────────────────────────────────────────

    def extract(self, file_bytes: bytes) -> ExtractedDocument:
        """
        Punto de entrada principal. Valida el PDF y retorna un ExtractedDocument.

        Args:
            file_bytes: Contenido del PDF como bytes (sin escritura en disco).

        Returns:
            ExtractedDocument con texto, checksum, page_count y metadata.

        Raises:
            PDFValidationError: Si el archivo no es PDF válido o es demasiado grande.
        """
        self.validate_pdf(file_bytes)
        reader = self._get_reader(file_bytes)

        return ExtractedDocument(
            text=self.extract_text(file_bytes),
            checksum=self.calculate_checksum(file_bytes),
            page_count=len(reader.pages),
            metadata=self.extract_metadata(file_bytes),
        )

    # ── Métodos públicos (también usados en tests unitarios) ──────

    def validate_pdf(self, file_bytes: bytes) -> bool:
        """
        Valida que los bytes correspondan a un PDF válido y dentro del límite de tamaño.

        Args:
            file_bytes: Contenido del archivo.

        Returns:
            True si el archivo es válido.

        Raises:
            PDFValidationError: Si el archivo no es válido.
        """
        if len(file_bytes) > self._max_bytes:
            raise PDFValidationError(
                f"El archivo supera el tamaño máximo de {self._max_bytes // (1024 * 1024)} MB."
            )
        if not file_bytes.startswith(b"%PDF"):
            raise PDFValidationError("El archivo no tiene la firma PDF válida (%PDF).")
        try:
            self._get_reader(file_bytes)
        except PdfReadError as exc:
            raise PDFValidationError(f"El archivo PDF está corrupto o no es válido: {exc}") from exc
        return True

    def calculate_checksum(self, file_bytes: bytes) -> str:
        """
        Calcula el checksum SHA-256 del archivo.

        Args:
            file_bytes: Contenido del archivo.

        Returns:
            Hash SHA-256 en formato hexadecimal (64 caracteres).
        """
        return hashlib.sha256(file_bytes).hexdigest()

    def extract_text(self, file_bytes: bytes) -> str:
        """
        Extrae el texto de todas las páginas del PDF.

        Args:
            file_bytes: Contenido del PDF como bytes.

        Returns:
            Texto concatenado de todas las páginas, separado por saltos de línea.
            Retorna string vacío si el PDF no contiene texto seleccionable.
        """
        reader = self._get_reader(file_bytes)
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
        return "\n".join(pages_text).strip()

    def extract_metadata(self, file_bytes: bytes) -> dict:
        """
        Extrae los metadatos del PDF (autor, título, fecha de creación, etc.).

        Args:
            file_bytes: Contenido del PDF como bytes.

        Returns:
            Diccionario con los metadatos disponibles. Claves con prefijo '/'
            de pypdf son normalizadas (e.g. '/Author' → 'author').
        """
        reader = self._get_reader(file_bytes)
        raw_meta = reader.metadata or {}
        return {
            key.lstrip("/").lower(): str(value)
            for key, value in raw_meta.items()
            if value is not None
        }

    # ── Método privado ────────────────────────────────────────────

    def _get_reader(self, file_bytes: bytes) -> PdfReader:
        """Crea un PdfReader en memoria (sin escritura en disco)."""
        return PdfReader(io.BytesIO(file_bytes))