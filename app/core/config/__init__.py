# config package
# Responsable de cargar y exponer la configuración desde variables de entorno.

from app.core.config.settings import Settings, settings

__all__ = ["Settings", "settings"]
