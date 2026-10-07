"""
Extracción de texto de un PDF en memoria (nunca se escribe a disco).

No sabe nada de HTTP: recibe bytes y devuelve el texto o una PDFValidationError.
"""
import io
import re
from dataclasses import dataclass

from pypdf import PasswordType, PdfReader
from pypdf.errors import PdfReadError


class PDFValidationError(ValueError):
    """Los bytes no son un PDF que se pueda procesar."""


@dataclass(frozen=True)
class ExtractionResult:
    content: str
    page_count: int


def extract(data: bytes) -> ExtractionResult:
    reader = _open(data)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return ExtractionResult(content=_clean_text(text), page_count=len(reader.pages))


def _open(data: bytes) -> PdfReader:
    """Abre el PDF una sola vez, validando firma, integridad y contraseña."""
    if not data.startswith(b"%PDF"):
        raise PDFValidationError("El archivo no tiene la firma PDF válida (%PDF).")
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise PDFValidationError(f"El archivo PDF está corrupto o no es válido: {exc}") from exc
    # Los PDFs con restricciones de propietario se abren con contraseña vacía.
    if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
        raise PDFValidationError(
            "El archivo PDF está protegido con contraseña y no se puede procesar."
        )
    return reader


def _clean_text(text: str) -> str:
    """Corrige artefactos de pypdf preservando la estructura del texto."""
    # pypdf a veces deja secuencias de escape literales (la barra y la n) en vez
    # del carácter real.
    text = text.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Caracteres de control no imprimibles; se conservan \n y \t.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Barras sueltas: artefactos del PDF, el texto real no las usa.
    text = text.replace("\\", "")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # Como máximo una línea en blanco entre párrafos.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
