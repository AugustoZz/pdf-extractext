"""
Tests unitarios para PDFExtractorService — Bloque 1C.
Sigue TDD: cada test documenta el comportamiento esperado
antes o en paralelo a la implementación (sub-issue 1B).
"""
import pytest

from app.services.extractor import (
    PDFExtractorService,
    PDFValidationError,
    ExtractedDocument,
)


# ── Fixtures locales ──────────────────────────────────────────────────────────
@pytest.fixture
def service() -> PDFExtractorService:
    """Instancia del servicio con límite de tamaño reducido para tests."""
    return PDFExtractorService(max_file_size_mb=10)


@pytest.fixture
def strict_service() -> PDFExtractorService:
    """Servicio con límite de 1 MB para forzar error de tamaño."""
    return PDFExtractorService(max_file_size_mb=1)


# ── Tests de validación ───────────────────────────────────────────────────────
class TestValidatePDF:
    def test_validate_pdf_valid_file(self, service, sample_pdf_bytes):
        """Un PDF válido debe retornar True sin lanzar excepción."""
        assert service.validate_pdf(sample_pdf_bytes) is True

    def test_validate_pdf_invalid_file(self, service, invalid_file_bytes):
        """Bytes que no son PDF deben lanzar PDFValidationError."""
        with pytest.raises(PDFValidationError):
            service.validate_pdf(invalid_file_bytes)

    def test_validate_pdf_exceeds_size_limit(self, strict_service, oversized_pdf_bytes):
        """PDF que supera el límite de tamaño debe lanzar PDFValidationError."""
        with pytest.raises(PDFValidationError, match="tamaño máximo"):
            strict_service.validate_pdf(oversized_pdf_bytes)

    def test_validate_pdf_missing_pdf_header(self, service):
        """Bytes sin firma %PDF deben lanzar PDFValidationError."""
        with pytest.raises(PDFValidationError):
            service.validate_pdf(b"PK\x03\x04")  # ZIP signature, not PDF


# ── Tests de checksum ─────────────────────────────────────────────────────────
class TestCalculateChecksum:
    def test_calculate_checksum_deterministic(self, service, sample_pdf_bytes):
        """El mismo archivo debe producir siempre el mismo checksum."""
        checksum1 = service.calculate_checksum(sample_pdf_bytes)
        checksum2 = service.calculate_checksum(sample_pdf_bytes)
        assert checksum1 == checksum2

    def test_calculate_checksum_different_files(
        self, service, sample_pdf_bytes, empty_pdf_bytes
    ):
        """Archivos distintos deben producir checksums distintos."""
        checksum1 = service.calculate_checksum(sample_pdf_bytes)
        checksum2 = service.calculate_checksum(empty_pdf_bytes)
        assert checksum1 != checksum2

    def test_calculate_checksum_is_sha256(self, service, sample_pdf_bytes):
        """El checksum debe ser un hash SHA-256 (64 caracteres hexadecimales)."""
        checksum = service.calculate_checksum(sample_pdf_bytes)
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)


# ── Tests de extracción de texto ──────────────────────────────────────────────
class TestExtractText:
    def test_extract_text_from_valid_pdf(self, service, sample_pdf_bytes):
        """Un PDF válido debe retornar un string (puede estar vacío si no tiene texto)."""
        text = service.extract_text(sample_pdf_bytes)
        assert isinstance(text, str)

    def test_extract_text_empty_pdf(self, service, empty_pdf_bytes):
        """Un PDF sin texto seleccionable debe retornar string vacío."""
        text = service.extract_text(empty_pdf_bytes)
        assert text == ""

    def test_extract_text_returns_string_type(self, service, sample_pdf_bytes):
        """extract_text siempre debe retornar str, nunca None."""
        result = service.extract_text(sample_pdf_bytes)
        assert result is not None
        assert isinstance(result, str)


# ── Tests de extracción de metadata ──────────────────────────────────────────
class TestExtractMetadata:
    def test_extract_metadata_returns_dict(self, service, sample_pdf_bytes):
        """extract_metadata debe retornar un dict."""
        metadata = service.extract_metadata(sample_pdf_bytes)
        assert isinstance(metadata, dict)

    def test_extract_metadata_keys_are_lowercase(self, service, sample_pdf_bytes):
        """Las claves del dict de metadata deben estar en minúsculas sin '/'."""
        metadata = service.extract_metadata(sample_pdf_bytes)
        for key in metadata:
            assert key == key.lower(), f"Clave '{key}' no está en minúsculas"
            assert not key.startswith("/"), f"Clave '{key}' no debe comenzar con '/'"

    def test_extract_metadata_author(self, service, sample_pdf_bytes):
        """El PDF de prueba debe contener el campo 'author'."""
        metadata = service.extract_metadata(sample_pdf_bytes)
        assert "author" in metadata
        assert metadata["author"] == "Test Author"

    def test_extract_metadata_title(self, service, sample_pdf_bytes):
        """El PDF de prueba debe contener el campo 'title'."""
        metadata = service.extract_metadata(sample_pdf_bytes)
        assert "title" in metadata
        assert metadata["title"] == "Test PDF"

    def test_extract_metadata_empty_pdf(self, service, empty_pdf_bytes):
        """Un PDF sin metadata debe retornar dict vacío o dict con pocos campos."""
        metadata = service.extract_metadata(empty_pdf_bytes)
        assert isinstance(metadata, dict)


# ── Tests del método principal extract() ─────────────────────────────────────
class TestExtract:
    def test_extract_returns_extracted_document(self, service, sample_pdf_bytes):
        """extract() debe retornar una instancia de ExtractedDocument."""
        result = service.extract(sample_pdf_bytes)
        assert isinstance(result, ExtractedDocument)

    def test_extract_document_has_all_fields(self, service, sample_pdf_bytes):
        """El ExtractedDocument retornado debe tener todos los campos requeridos."""
        result = service.extract(sample_pdf_bytes)
        assert hasattr(result, "text")
        assert hasattr(result, "checksum")
        assert hasattr(result, "page_count")
        assert hasattr(result, "metadata")

    def test_extract_page_count_positive(self, service, sample_pdf_bytes):
        """Un PDF válido debe tener page_count >= 1."""
        result = service.extract(sample_pdf_bytes)
        assert result.page_count >= 1

    def test_extract_invalid_pdf_raises(self, service, invalid_file_bytes):
        """extract() debe propagar PDFValidationError para archivos inválidos."""
        with pytest.raises(PDFValidationError):
            service.extract(invalid_file_bytes)
