"""
Configuración centralizada de la aplicación (12-Factor App — Factor III).

Lee variables de entorno y del archivo .env usando pydantic-settings y, si
CONSUL_ENABLED es verdadero, las pisa con las claves del KV de Consul.
Todas las demás partes de la app deben importar ``settings`` desde aquí;
nunca leer os.environ directamente en otros módulos.
"""
import logging
from typing import Callable

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.consul.kv import read_kv_config

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Configuración de la aplicación leída desde variables de entorno.

    Orden de precedencia (ver ``load_settings``):
        1. Claves del KV de Consul, si CONSUL_ENABLED es verdadero.
        2. Variables de entorno del sistema operativo.
        3. Variables definidas en el archivo .env.
        4. Valores por defecto declarados en esta clase.

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

    # ── Servidor (12-Factor VII — Port Binding) ───────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Base de Datos (MongoDB) — configurado en Bloque 2 ─────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pdf_extractext"
    # Base separada para los tests de integración: nunca debe coincidir con
    # MONGODB_DB_NAME, porque la suite borra la colección al empezar y terminar.
    MONGODB_TEST_DB_NAME: str = "pdf_extractext_test"

    # ── Validación de PDF ─────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = Field(default=10, gt=0)
    PDF_ALLOWED_MIME_TYPE: str = "application/pdf"

    # Servicio HTTP externo; el nombre extractor es resuelto por Docker Compose.
    EXTRACTOR_URL: str = "http://extractor-lb/extract"
    EXTRACTOR_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)

    # ── Circuit breaker hacia el extractor ────────────────────────
    # Tras N fallos seguidos, se deja de llamar al extractor durante
    # RECOVERY segundos y se responde 503 enseguida.
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, ge=1)
    CIRCUIT_BREAKER_RECOVERY_SECONDS: float = Field(default=30.0, gt=0)

    # ── Consul: descubrimiento de servicios y configuración ───────
    # Desactivado por defecto: sin Consul la app usa EXTRACTOR_URL y el entorno.
    CONSUL_ENABLED: bool = False
    CONSUL_URL: str = "http://localhost:8500"
    CONSUL_EXTRACTOR_SERVICE: str = "extractor"
    CONSUL_KV_PREFIX: str = "config/pdf-extractext"
    CONSUL_CACHE_SECONDS: float = Field(default=10.0, ge=0)
    CONSUL_TIMEOUT_SECONDS: float = Field(default=2.0, gt=0)

    # ── CORS ──────────────────────────────────────────────────────
    # Lista de orígenes separados por coma. "*" (por defecto) sólo es
    # aceptable en desarrollo; en producción declarar los dominios reales.
    CORS_ALLOW_ORIGINS: str = "*"

    @property
    def cors_origins(self) -> list[str]:
        """Orígenes permitidos por CORS, ya parseados como lista."""
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """True si la app corre en un entorno productivo."""
        return self.APP_ENV.lower() == "production"


# Cómo llegar a Consul no puede venir de Consul: eso sólo se configura por entorno.
_BOOTSTRAP_KEYS = frozenset(name for name in Settings.model_fields if name.startswith("CONSUL_"))


def load_settings(read_kv: Callable[..., dict[str, str]] = read_kv_config) -> Settings:
    """
    Construye la configuración: entorno primero y, si está habilitado, Consul encima.

    Un valor inválido en Consul (p. ej. MAX_FILE_SIZE_MB=-1) hace fallar el
    arranque con el error de validación: mejor no arrancar que arrancar mal.
    """
    base = Settings()
    if not base.CONSUL_ENABLED:
        return base

    remote = read_kv(
        base.CONSUL_URL, base.CONSUL_KV_PREFIX, timeout_seconds=base.CONSUL_TIMEOUT_SECONDS
    )
    overrides = {
        name: value
        for name, value in remote.items()
        if name in Settings.model_fields and name not in _BOOTSTRAP_KEYS
    }
    ignored = sorted(set(remote) - set(overrides))
    if ignored:
        logger.warning("Claves de Consul ignoradas (desconocidas o de arranque): %s", ignored)
    if not overrides:
        return base
    logger.info("Configuración tomada de Consul: %s", sorted(overrides))
    # Los argumentos del constructor tienen prioridad sobre el entorno.
    return Settings(**overrides)


# Singleton — importar esta instancia en toda la app
settings = load_settings()
