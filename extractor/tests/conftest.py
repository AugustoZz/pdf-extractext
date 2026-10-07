"""PDFs de prueba generados en memoria (sin archivos en disco)."""
import io

import pytest
from pypdf import PdfWriter

from tests.pdf_factory import build_pdf


def _encrypted_pdf(user_password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt(user_password=user_password, owner_password="owner")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def text_pdf() -> bytes:
    return build_pdf("Hola mundo")


@pytest.fixture
def blank_pdf() -> bytes:
    """PDF válido sin texto seleccionable, como uno escaneado sin OCR."""
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def password_pdf() -> bytes:
    """Requiere contraseña para abrirse."""
    return _encrypted_pdf(user_password="secreta")


@pytest.fixture
def owner_restricted_pdf() -> bytes:
    """Cifrado con restricciones de propietario, pero se abre sin contraseña."""
    return _encrypted_pdf(user_password="")
