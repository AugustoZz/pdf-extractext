"""
Configuración centralizada de la aplicación (12-Factor App — Factor III).

Lee variables de entorno y del archivo .env usando pydantic-settings.
Todas las demás partes de la app deben importar ``settings`` desde aquí;
nunca leer os.environ directamente en otros módulos.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación leída desde variables de entorno.

    Orden de precedencia:
        1. Variables de entorno del sistema operativo.
        2. Variables definidas en el archivo .env.
        3. Valores por defecto declarados en esta clase.

    Uso::

        from app.core.config import settings
        print(settings.MONGODB_URI)
        print(settings.MAX_FILE_SIZE_MB)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicación ────────────────────────────────────────────────
    APP_NAME: str = "pdf-extractext"
    APP_ENV: str = "development"  # development | production | testing
    LOG_LEVEL: str = "INFO"       # DEBUG | INFO | WARNING | ERROR | CRITICAL

    # ── Base de Datos (MongoDB) — configurado en Bloque 2 ─────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pdf_extractext"

    # ── Validación de PDF ─────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    PDF_ALLOWED_MIME_TYPE: str = "application/pdf"


# Singleton — importar esta instancia en toda la app
settings = Settings()
