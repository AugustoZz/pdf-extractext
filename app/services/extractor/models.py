"""
Modelos de datos del servicio de extracción PDF.

Contrato compartido entre PDFExtractorService y la capa de API/DB.
Este módulo NO contiene lógica de negocio (Principio SRP).
"""
from dataclasses import dataclass, field


@dataclass
class ExtractedDocument:
    """
    Representa el resultado de extraer texto de un archivo PDF.

    Atributos:
        text (str): Texto extraído de todas las páginas del PDF,
            concatenado y separado por saltos de línea. Puede ser
            vacío si el PDF no contiene texto seleccionable
            (por ejemplo, un PDF escaneado sin OCR).
        checksum (str): Hash SHA-256 del archivo original en formato
            hexadecimal (64 caracteres). Usado para detectar
            documentos duplicados en la base de datos.
        page_count (int): Número total de páginas del PDF.
        metadata (dict): Metadatos del PDF (autor, título, fecha de
            creación, etc.). Las claves están en minúsculas y sin el
            prefijo '/'. Puede ser un dict vacío si el PDF no tiene
            metadatos definidos.
    """

    text: str
    checksum: str
    page_count: int
    metadata: dict = field(default_factory=dict)
