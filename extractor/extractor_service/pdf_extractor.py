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
        blocks = [
            spans
            for page in doc
            for block in page.get_text("dict", flags=_TEXT_FLAGS, sort=True)["blocks"]
            if (spans := _text_spans(block))
        ]
        return ExtractionResult(content=_to_markdown(blocks), page_count=doc.page_count)


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


def _text_spans(block: dict) -> list[dict]:
    """Fragmentos con texto de un bloque (los bloques de imagen no tienen líneas)."""
    return [span for line in block.get("lines", []) for span in line["spans"] if span["text"].strip()]


def _to_markdown(blocks: list[list[dict]]) -> str:
    # El cuerpo es el tamaño de letra más usado del documento.
    sizes = Counter(round(span["size"]) for spans in blocks for span in spans)
    body_size = sizes.most_common(1)[0][0] if sizes else 0
    return "\n\n".join(_block_to_markdown(spans, body_size) for spans in blocks)


def _block_to_markdown(spans: list[dict], body_size: float) -> str:
    text = " ".join(span["text"].strip() for span in spans)
    size = max(span["size"] for span in spans)
    if size >= body_size * _HEADING_RATIO:
        return f"# {text}"
    if size >= body_size * _SUBHEADING_RATIO:
        return f"## {text}"
    if all(span["flags"] & pymupdf.TEXT_FONT_BOLD for span in spans):
        return f"**{text}**"
    return text
