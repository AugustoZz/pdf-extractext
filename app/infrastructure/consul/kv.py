"""
Configuración centralizada en el KV de Consul (12-Factor III).

Lee todas las claves bajo un prefijo, por ejemplo::

    config/pdf-extractext/EXTRACTOR_TIMEOUT_SECONDS = 30
    config/pdf-extractext/CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5

y devuelve ``{"EXTRACTOR_TIMEOUT_SECONDS": "30", ...}``. Es síncrono porque se
usa una sola vez, al construir ``Settings`` durante el arranque.

Si Consul no responde, devuelve ``{}`` y la app sigue con sus variables de
entorno: la configuración central es una mejora, no un requisito para arrancar.
"""
import base64
import binascii
import logging

import httpx

logger = logging.getLogger(__name__)


def read_kv_config(
    consul_url: str,
    prefix: str,
    *,
    timeout_seconds: float = 2.0,
    client: httpx.Client | None = None,
) -> dict[str, str]:
    prefix = prefix.strip("/")
    url = f"{consul_url.rstrip('/')}/v1/kv/{prefix}/"
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_seconds, trust_env=False)
    try:
        response = http.get(url, params={"recurse": ""})
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        entries = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "No se pudo leer la configuración de Consul (%s); se usan las variables de entorno.",
            type(exc).__name__,
        )
        return {}
    finally:
        if owns_client:
            http.close()

    config: dict[str, str] = {}
    for entry in entries:
        name = entry.get("Key", "")[len(prefix) + 1:]
        raw = entry.get("Value")
        # Carpetas (sin valor) y claves anidadas no son parte de la configuración.
        if not name or "/" in name or raw is None:
            continue
        try:
            config[name.upper()] = base64.b64decode(raw).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            logger.warning("Valor ilegible en Consul para %s; se ignora.", name)
    return config
