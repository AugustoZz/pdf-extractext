"""Configuración por variables de entorno (12-Factor III)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MAX_FILE_SIZE_MB: int = 10
    # Procesos que extraen en paralelo; con 1 CPU por réplica, más no suma.
    WORKERS: int = 1
    # Cuánto puede esperar una petición antes de recibir 503: por debajo del
    # timeout de Vegeta (30 s), pero sin cortar de más en el spike de k6. Con
    # 10 s k6 tenía 15 % de errores; con 20 s, ninguno (docs/informe-carga.md).
    QUEUE_TIMEOUT_S: float = 20.0

    @property
    def max_file_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
