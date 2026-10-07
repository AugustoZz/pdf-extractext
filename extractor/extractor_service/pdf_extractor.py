"""
Extracción del texto de un PDF como Markdown, en memoria (nunca se escribe a disco).

No sabe nada de HTTP: recibe bytes y devuelve el Markdown o una PDFValidationError.
Usa PyMuPDF (licencia AGPL) a través de pymupdf4llm.
"""
from dataclasses import dataclass

import pymupdf
import pymupdf4llm

# pymupdf4llm usa por defecto un modelo de IA para analizar el layout: es de 5 a 7
# veces más lento que pypdf. El conversor clásico, sin tablas, imágenes ni
# gráficos, es ~2,5 veces más rápido que pypdf y da Markdown (ver #32).
pymupdf4llm.use_layout(False)
_MARKDOWN_OPTIONS = {
    "table_strategy": None,
    "ignore_images": True,
    "ignore_graphics": True,
    "show_progress": False,
}


class PDFValidationError(ValueError):
    """Los bytes no son un PDF que se pueda procesar."""


@dataclass(frozen=True)
class ExtractionResult:
    content: str
    page_count: int


def extract(data: bytes) -> ExtractionResult:
    with _open(data) as doc:
        content = pymupdf4llm.to_markdown(doc, **_MARKDOWN_OPTIONS)
        return ExtractionResult(content=content.strip(), page_count=doc.page_count)


def _open(data: bytes) -> pymupdf.Document:
    """Abre el PDF validando firma, integridad y contraseña."""
    if not data.startswith(b"%PDF"):
        raise PDFValidationError("El archivo no tiene la firma PDF válida (%PDF).")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except pymupdf.FileDataError as exc:
        raise PDFValidationError(f"El archivo PDF está corrupto o no es válido: {exc}") from exc
    # PyMuPDF repara lo que puede; si no rescata ninguna página, está corrupto.
    if doc.page_count == 0:
        doc.close()
        raise PDFValidationError("El archivo PDF está corrupto o no es válido: no tiene páginas.")
    # Los PDFs con restricciones de propietario se abren sin contraseña.
    if doc.needs_pass:
        doc.close()
        raise PDFValidationError(
            "El archivo PDF está protegido con contraseña y no se puede procesar."
        )
    return doc
