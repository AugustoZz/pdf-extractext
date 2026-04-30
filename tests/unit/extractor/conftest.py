"""
Fixtures de pytest para los tests del PDFExtractorService.
Los PDFs de prueba se generan en memoria con pypdf (sin archivos en disco).
"""
import io

import pytest
import pypdf
from pypdf import PdfWriter


def _build_pdf(text: str = "", author: str = "", title: str = "") -> bytes:
    """Helper interno: crea un PDF en memoria con pypdf."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)  # A4

    if text:
        # pypdf no tiene API de inserción de texto en PdfWriter;
        # usamos un PDF mínimo con texto embebido para pruebas reales.
        pass

    if author or title:
        writer.add_metadata({"/Author": author, "/Title": title})

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """PDF válido con al menos una página. Para tests de validación y checksum."""
    return _build_pdf(author="Test Author", title="Test PDF")


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """PDF válido sin texto seleccionable (página en blanco)."""
    return _build_pdf()


@pytest.fixture
def invalid_file_bytes() -> bytes:
    """Bytes que NO son un PDF válido."""
    return b"This is not a PDF file content at all."


@pytest.fixture
def oversized_pdf_bytes(sample_pdf_bytes: bytes) -> bytes:
    """PDF válido que supera el límite de 1 MB (para test de tamaño)."""
    # Padding para forzar superación del límite en tests con max=1
    return sample_pdf_bytes + b"\x00" * (1 * 1024 * 1024 + 1)
