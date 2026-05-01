"""
Repositorio para operar con la colección de documentos en MongoDB.
"""
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.database.connection import get_database

COLLECTION_NAME = "documents"

class DocumentRepository:
    
    @classmethod
    def _collection(cls):
        return get_database()[COLLECTION_NAME]

    @classmethod
    async def get_by_checksum(cls, checksum: str) -> Optional[dict]:
        """Busca un documento por su checksum (para evitar duplicados)."""
        doc = await cls._collection().find_one({"checksum": checksum})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    @classmethod
    async def create(cls, data: dict) -> dict:
        """Crea un nuevo documento en la base de datos."""
        result = await cls._collection().insert_one(data)
        return await cls.get_by_id(str(result.inserted_id))

    @classmethod
    async def get_by_id(cls, doc_id: str) -> Optional[dict]:
        """Obtiene un documento por su ID."""
        if not ObjectId.is_valid(doc_id):
            return None
        doc = await cls._collection().find_one({"_id": ObjectId(doc_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    @classmethod
    async def get_all(cls, skip: int = 0, limit: int = 100) -> List[dict]:
        """Devuelve una lista paginada de documentos."""
        cursor = cls._collection().find().skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            docs.append(doc)
        return docs

    @classmethod
    async def update(cls, doc_id: str, data: dict) -> Optional[dict]:
        """Actualiza parcialmente un documento."""
        if not ObjectId.is_valid(doc_id):
            return None
        # Removemos _id y id si vienen en la data
        data.pop("_id", None)
        data.pop("id", None)
        
        result = await cls._collection().update_one(
            {"_id": ObjectId(doc_id)}, {"$set": data}
        )
        if result.modified_count == 0 and result.matched_count == 0:
            return None
        return await cls.get_by_id(doc_id)

    @classmethod
    async def delete(cls, doc_id: str) -> bool:
        """Elimina un documento de la base de datos."""
        if not ObjectId.is_valid(doc_id):
            return False
        result = await cls._collection().delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
