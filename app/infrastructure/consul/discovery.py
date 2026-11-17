"""
Descubrimiento de servicios: ¿a qué URL le pego para llegar al extractor?

``StaticURLResolver`` devuelve siempre la URL configurada (sin Consul).
``ConsulServiceResolver`` le pregunta a Consul por las instancias SANAS del
servicio (``/v1/health/service/<nombre>?passing=true``), es decir, las que
pasan su health check, y elige una.

Decisiones:
- Caché corta (``cache_seconds``): evita un salto de red a Consul por cada PDF.
- Si Consul no responde, se usan las últimas instancias conocidas y, si no
  hay, la URL de respaldo (``EXTRACTOR_URL``). Consul no debe ser un punto
  único de falla: que se caiga no tiene que tirar la extracción.
- Si Consul SÍ responde pero no hay instancias sanas, es un error: usar el
  respaldo sería ignorar el health check.
"""
import logging
import random
import time
from typing import Callable, Protocol

import httpx

logger = logging.getLogger(__name__)


class NoHealthyInstanceError(RuntimeError):
    """No hay ninguna instancia sana del servicio a la que llamar."""


class ServiceResolver(Protocol):
    async def start(self) -> None: ...
    async def close(self) -> None: ...
    async def resolve(self) -> str: ...


class StaticURLResolver:
    """URL fija (configuración por variable de entorno)."""

    def __init__(self, url: str):
        self._url = url

    async def start(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def resolve(self) -> str:
        return self._url


class ConsulServiceResolver:
    def __init__(
        self,
        consul_url: str,
        service_name: str,
        *,
        path: str = "/",
        fallback_url: str | None = None,
        cache_seconds: float = 10.0,
        timeout_seconds: float = 2.0,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] = time.monotonic,
        chooser: Callable[[list[str]], str] = random.choice,
    ):
        self._endpoint = f"{consul_url.rstrip('/')}/v1/health/service/{service_name}"
        self._service_name = service_name
        self._path = path if path.startswith("/") else f"/{path}"
        self._fallback_url = fallback_url
        self._cache_seconds = cache_seconds
        self._timeout = timeout_seconds
        self._client = client
        self._owns_client = client is None
        self._clock = clock
        self._choose = chooser
        self._instances: list[str] = []
        self._expires_at = 0.0

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, trust_env=False)

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def resolve(self) -> str:
        if self._instances and self._clock() < self._expires_at:
            return self._choose(self._instances)

        try:
            instances = await self._healthy_instances()
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return self._degraded_url(exc)

        if not instances:
            self._instances = []
            raise NoHealthyInstanceError(
                f"Consul no tiene instancias sanas de '{self._service_name}'."
            )
        self._instances = instances
        self._expires_at = self._clock() + self._cache_seconds
        return self._choose(instances)

    async def _healthy_instances(self) -> list[str]:
        if self._client is None:
            raise httpx.RequestError("El cliente de Consul no está inicializado.")
        response = await self._client.get(self._endpoint, params={"passing": "true"})
        response.raise_for_status()
        urls = []
        for entry in response.json():
            service = entry["Service"]
            address = service.get("Address") or entry["Node"]["Address"]
            urls.append(f"http://{address}:{int(service['Port'])}{self._path}")
        return urls

    def _degraded_url(self, exc: Exception) -> str:
        if self._instances:
            logger.warning(
                "Consul no responde (%s); se usan las últimas instancias conocidas.",
                type(exc).__name__,
            )
            return self._choose(self._instances)
        if self._fallback_url:
            logger.warning(
                "Consul no responde (%s); se usa la URL de respaldo.", type(exc).__name__
            )
            return self._fallback_url
        raise NoHealthyInstanceError("Consul no responde y no hay URL de respaldo.") from exc
