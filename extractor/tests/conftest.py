"""PDFs de prueba generados en memoria (sin archivos en disco)."""
import pymupdf
import pytest

from tests.pdf_factory import build_pdf


def _blank_pdf(user_password: str | None = None) -> bytes:
    """Una página en blanco; con user_password, además cifrado."""
    doc = pymupdf.open()
    doc.new_page(width=72, height=72)
    if user_password is None:
        return doc.tobytes()
    return doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=user_password, owner_pw="owner"
    )


@pytest.fixture
def text_pdf() -> bytes:
    return build_pdf("Hola mundo")


@pytest.fixture
def blank_pdf() -> bytes:
    """PDF válido sin texto seleccionable, como uno escaneado sin OCR."""
    return _blank_pdf()


@pytest.fixture
def password_pdf() -> bytes:
    """Requiere contraseña para abrirse."""
    return _blank_pdf(user_password="secreta")


@pytest.fixture
def owner_restricted_pdf() -> bytes:
    """Cifrado con restricciones de propietario, pero se abre sin contraseña."""
    return _blank_pdf(user_password="")
