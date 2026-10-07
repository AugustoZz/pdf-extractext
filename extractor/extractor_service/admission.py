"""
Control de admisión (backpressure).

Limita cuántos PDFs se procesan a la vez. Si una petición no consigue lugar a
tiempo se la rechaza, en vez de dejarla esperar hasta que el cliente corte por
timeout: procesar una petición abandonada es CPU tirada.
"""
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class Saturated(Exception):
    """No se liberó ningún lugar dentro del tiempo de espera."""


class Admission:
    def __init__(self, capacity: int, wait_timeout: float) -> None:
        self._slots = asyncio.Semaphore(capacity)
        self._wait_timeout = wait_timeout

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(self._slots.acquire(), self._wait_timeout)
        except TimeoutError as exc:
            raise Saturated from exc
        try:
            yield
        finally:
            self._slots.release()
