# Integración con Consul: descubrimiento de servicios y configuración KV.
from app.infrastructure.consul.discovery import (
    ConsulServiceResolver,
    NoHealthyInstanceError,
    ServiceResolver,
    StaticURLResolver,
)
from app.infrastructure.consul.kv import read_kv_config

__all__ = [
    "ConsulServiceResolver",
    "NoHealthyInstanceError",
    "ServiceResolver",
    "StaticURLResolver",
    "read_kv_config",
]
