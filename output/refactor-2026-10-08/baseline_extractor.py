"""
Extracción del texto de un PDF como Markdown, en memoria (nunca se escribe a disco).

No sabe nada de HTTP: recibe bytes y devuelve el Markdown o una PDFValidationError.
Usa PyMuPDF (licencia AGPL), con un conversor a Markdown propio y liviano: cada
bloque de texto es un párrafo, el texto más grande que el cuerpo es un título y
el texto todo en negrita va entre `**`. pymupdf4llm da un Markdown más rico pero
es ~14 veces más lento con los PDFs del TP (ver docs/informe-carga.md).
"""
from collections import Counter
from dataclasses import dataclass

import pymupdf

# A partir de cuántas veces el tamaño del cuerpo un bloque es título (#) o subtítulo (##).
_HEADING_RATIO = 1.5
_SUBHEADING_RATIO = 1.2
_TEXT_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP


class PDFValidationError(ValueError):
    """Los bytes no son un PDF que se pueda procesar."""


@dataclass(frozen=True)
class ExtractionResult:
    content: str
    page_count: int


def extract(data: bytes) -> ExtractionResult:
    with _open(data) as doc:
        # Sólo conservamos lo necesario para Markdown, no el árbol completo de
        # geometría, fuentes y colores de todas las páginas. El tamaño del cuerpo
        # sigue calculándose sobre todos los spans del documento.
        blocks: list[tuple[str, float, bool]] = []
        sizes: list[int] = []
        for page in doc:
            page_blocks = page.get_textpage(flags=_TEXT_FLAGS).extractDICT(sort=True)["blocks"]
            for block in page_blocks:
                parts = []
                maximum_size = 0.0
                bold = True
                for line in block.get("lines", ()):
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        parts.append(text)
                        size = span["size"]
                        sizes.append(round(size))
                        if size > maximum_size:
                            maximum_size = size
                        bold = bold and bool(span["flags"] & pymupdf.TEXT_FONT_BOLD)
                if parts:
                    blocks.append((" ".join(parts), maximum_size, bold))
        body_size = Counter(sizes).most_common(1)[0][0] if sizes else 0
        headings = body_size * _HEADING_RATIO
        subheadings = body_size * _SUBHEADING_RATIO
        paragraphs = []
        for text, size, bold in blocks:
            if size >= headings:
                text = f"# {text}"
            elif size >= subheadings:
                text = f"## {text}"
            elif bold:
                text = f"**{text}**"
            paragraphs.append(text)
        return ExtractionResult(content="\n\n".join(paragraphs), page_count=doc.page_count)


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
