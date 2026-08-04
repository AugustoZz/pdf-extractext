"""
Endpoints CRUD para documentos persistidos en la base de datos.
"""
from fastapi import APIRouter, HTTPException, Query

from app.api.v1.schemas import DocumentUpdate
from app.infrastructure.database.repository import DocumentRepository

router = APIRouter()

@router.get(
    "/documents",
    summary="Listar documentos",
    response_description="Lista paginada de documentos extraídos."
)
async def list_documents(
    skip: int = Query(default=0, ge=0, description="Documentos a omitir."),
    limit: int = Query(default=100, ge=1, le=500, description="Máximo de documentos a devolver."),
):
    """Devuelve todos los documentos guardados en la BD."""
    docs = await DocumentRepository.get_all(skip=skip, limit=limit)
    return {"data": docs}

@router.get(
    "/documents/{doc_id}",
    summary="Obtener un documento por ID",
    response_description="Los detalles de un documento específico."
)
async def get_document(doc_id: str):
    """Obtiene un documento persistido usando su ID único."""
    doc = await DocumentRepository.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc

@router.put(
    "/documents/{doc_id}",
    summary="Actualizar un documento",
    response_description="El documento actualizado."
)
async def update_document(doc_id: str, data: DocumentUpdate):
    """
    Actualiza parcialmente los campos de un documento.
    (Ej: actualizar metadatos o corregir alguna extracción manual).
    """
    changes = data.to_changes()
    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Debe enviarse al menos un campo para actualizar.",
        )

    doc = await DocumentRepository.update(doc_id, changes)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc

@router.delete(
    "/documents/{doc_id}",
    summary="Eliminar un documento",
    response_description="Estado de la eliminación."
)
async def delete_document(doc_id: str):
    """Elimina permanentemente un documento de la BD."""
    success = await DocumentRepository.delete(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {"status": "ok", "message": "Documento eliminado con éxito"}
