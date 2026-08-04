"""
Repositorio para operar con la colección de documentos en MongoDB.
"""
import logging
from typing import List, Optional

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.infrastructure.database.connection import get_database

logger = logging.getLogger(__name__)

COLLECTION_NAME = "documents"

# Campos derivados del archivo original: no se pueden modificar vía API.
# Reescribir el checksum rompería la detección de duplicados.
IMMUTABLE_FIELDS = ("_id", "id", "checksum")

class DocumentRepository:

    @classmethod
    def _collection(cls):
        return get_database()[COLLECTION_NAME]

    @classmethod
    async def ensure_indexes(cls) -> None:
        """
        Crea los índices necesarios en la colección.

        El índice único sobre ``checksum`` es lo que realmente impide documentos
        duplicados: la verificación previa en el endpoint no alcanza, porque dos
        subidas simultáneas del mismo PDF pueden pasar el chequeo antes de que
        cualquiera de las dos inserte.
        """
        try:
            await cls._collection().create_index("checksum", unique=True, name="uq_checksum")
            logger.info("Índice único sobre 'checksum' verificado.")
        except PyMongoError as exc:
            # No abortamos el arranque: lo más probable es que ya existan
            # documentos duplicados de antes de introducir el índice.
            logger.error(
                "No se pudo crear el índice único sobre 'checksum': %s. "
                "Es probable que existan duplicados previos en la colección; "
                "limpialos y reiniciá la aplicación.",
                exc,
            )

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
        """
        Actualiza parcialmente un documento.

        Args:
            doc_id: ID del documento a actualizar.
            data: Campos a modificar. Los campos inmutables se descartan.

        Returns:
            El documento actualizado, o None si el ID no existe / no es válido.
        """
        if not ObjectId.is_valid(doc_id):
            return None

        # Copia: no mutamos el diccionario que nos pasó el llamador.
        changes = {key: value for key, value in data.items() if key not in IMMUTABLE_FIELDS}

        # Sin campos válidos no hay nada que actualizar. Mongo rechaza un
        # "$set" vacío, así que devolvemos el documento tal cual está.
        if not changes:
            return await cls.get_by_id(doc_id)

        result = await cls._collection().update_one(
            {"_id": ObjectId(doc_id)}, {"$set": changes}
        )
        if result.matched_count == 0:
            return None
        return await cls.get_by_id(doc_id)

    @classmethod
    async def delete(cls, doc_id: str) -> bool:
        """Elimina un documento de la base de datos."""
        if not ObjectId.is_valid(doc_id):
            return False
        result = await cls._collection().delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
