"""
Esquemas de entrada/salida de la API v1.

Definen el contrato HTTP y validan lo que llega desde el cliente antes de que
toque la capa de datos. Este módulo NO contiene lógica de negocio (Principio SRP).
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentUpdate(BaseModel):
    """
    Campos modificables de un documento (actualización parcial).

    Sólo se listan los campos que el usuario puede editar: ``checksum``,
    ``page_count`` y ``created_at`` derivan del archivo original y se omiten
    a propósito para que no puedan reescribirse desde la API.
    """

    model_config = ConfigDict(extra="forbid")

    filename: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nombre del archivo mostrado en la interfaz.",
    )
    text: Optional[str] = Field(
        default=None,
        description="Texto extraído, editable para correcciones manuales.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos del PDF (autor, título, etc.).",
    )

    def to_changes(self) -> Dict[str, Any]:
        """Devuelve sólo los campos efectivamente enviados por el cliente."""
        return self.model_dump(exclude_unset=True, exclude_none=True)
