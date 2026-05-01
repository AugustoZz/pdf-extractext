"""
Conexión a MongoDB utilizando Motor (Asyncio).
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_instance = Database()

async def connect_to_mongo():
    """Establece conexión con MongoDB."""
    logger.info(f"Conectando a MongoDB en {settings.MONGODB_URI}...")
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_instance.db = db_instance.client[settings.MONGODB_DB_NAME]
    logger.info("Conexión a MongoDB establecida.")

async def close_mongo_connection():
    """Cierra la conexión con MongoDB."""
    if db_instance.client:
        logger.info("Cerrando conexión a MongoDB...")
        db_instance.client.close()
        logger.info("Conexión a MongoDB cerrada.")

def get_database() -> AsyncIOMotorDatabase:
    """Devuelve la instancia de la base de datos."""
    return db_instance.db
