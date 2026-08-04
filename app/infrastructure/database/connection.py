"""
Conexión a MongoDB utilizando Motor (Asyncio).
"""
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tiempo máximo de espera al seleccionar servidor durante el arranque.
_SERVER_SELECTION_TIMEOUT_MS = 5000


class DatabaseConnectionError(RuntimeError):
    """Se lanza cuando no se puede establecer conexión con MongoDB."""


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_instance = Database()

async def connect_to_mongo(db_name: Optional[str] = None):
    """
    Establece conexión con MongoDB y verifica que el servidor responda.

    Args:
        db_name: Nombre de la base a usar. Por defecto ``settings.MONGODB_DB_NAME``.
            Los tests de integración pasan aquí la base de test.

    Raises:
        DatabaseConnectionError: Si el servidor no responde. Se falla rápido
            en el arranque en lugar de dejar la app viva con una BD inutilizable.
    """
    target_db = db_name or settings.MONGODB_DB_NAME
    logger.info("Conectando a MongoDB en %s (base: %s)...", settings.MONGODB_URI, target_db)

    client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=_SERVER_SELECTION_TIMEOUT_MS,
    )
    try:
        # ``ping`` fuerza la conexión real: sin esto Motor es perezoso y el
        # error recién aparecería en el primer request.
        await client.admin.command("ping")
    except PyMongoError as exc:
        client.close()
        logger.error("No se pudo conectar a MongoDB en %s: %s", settings.MONGODB_URI, exc)
        raise DatabaseConnectionError(
            f"No se pudo conectar a MongoDB en {settings.MONGODB_URI}. "
            "Verificá que el servicio esté levantado (docker compose up)."
        ) from exc

    db_instance.client = client
    db_instance.db = client[target_db]
    logger.info("Conexión a MongoDB establecida.")

async def close_mongo_connection():
    """Cierra la conexión con MongoDB."""
    if db_instance.client:
        logger.info("Cerrando conexión a MongoDB...")
        db_instance.client.close()
        db_instance.client = None
        db_instance.db = None
        logger.info("Conexión a MongoDB cerrada.")

def get_database() -> AsyncIOMotorDatabase:
    """
    Devuelve la instancia de la base de datos.

    Raises:
        DatabaseConnectionError: Si se invoca antes de ``connect_to_mongo``.
    """
    if db_instance.db is None:
        raise DatabaseConnectionError(
            "La base de datos no está inicializada: llamá a connect_to_mongo() primero."
        )
    return db_instance.db
