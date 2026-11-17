"""
Circuit breaker (cortocircuito) para llamadas a otro servicio.

Estados:
    CLOSED     — normal: las llamadas pasan y se cuentan los fallos seguidos.
    OPEN       — tras ``failure_threshold`` fallos seguidos: se rechaza enseguida,
                 sin llamar, durante ``recovery_timeout`` segundos.
    HALF_OPEN  — pasado ese tiempo: deja pasar UNA llamada de prueba. Si sale
                 bien, cierra; si falla, vuelve a abrir por otro período entero.

Uso desde quien llama::

    breaker.before_call()          # CircuitOpenError si está abierto
    try:
        resultado = await llamar()
    except FalloDelServicio:
        breaker.record_failure()
        raise
    except asyncio.CancelledError:
        breaker.release()          # la llamada no terminó: no es éxito ni fallo
        raise
    else:
        breaker.record_success()

No usa locks: corre en el event loop de asyncio y ningún método espera (await),
así que no hay intercalado entre la consulta y el cambio de estado.
"""
import logging
import time
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """El circuito está abierto: no se intenta la llamada."""

    def __init__(self, name: str, retry_after: float):
        super().__init__(f"Circuito '{name}' abierto; reintentar en {retry_after:.0f} s.")
        self.retry_after = retry_after


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold debe ser al menos 1.")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout debe ser mayor que 0.")
        self.name = name
        self._threshold = failure_threshold
        self._recovery = recovery_timeout
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._trial_in_flight = False

    @property
    def state(self) -> CircuitState:
        return self._state

    def before_call(self) -> None:
        """Deja pasar la llamada o lanza ``CircuitOpenError``."""
        if self._state is CircuitState.CLOSED:
            return
        if self._state is CircuitState.OPEN:
            remaining = self._opened_at + self._recovery - self._clock()
            if remaining > 0:
                raise CircuitOpenError(self.name, remaining)
            self._state = CircuitState.HALF_OPEN
            logger.info("Circuito '%s' semiabierto: se prueba una llamada.", self.name)
        # HALF_OPEN: una sola llamada de prueba a la vez.
        if self._trial_in_flight:
            raise CircuitOpenError(self.name, 0.0)
        self._trial_in_flight = True

    def record_success(self) -> None:
        if self._state is CircuitState.CLOSED:
            self._failures = 0
        elif self._state is CircuitState.HALF_OPEN and self._trial_in_flight:
            self._close()
        # OPEN: es una llamada que empezó antes de abrir; no cambia nada.

    def record_failure(self) -> None:
        if self._state is CircuitState.CLOSED:
            self._failures += 1
            if self._failures >= self._threshold:
                self._open()
        elif self._state is CircuitState.HALF_OPEN and self._trial_in_flight:
            self._open()

    def release(self) -> None:
        """La llamada no terminó (p. ej. se canceló): libera la prueba sin juzgarla."""
        if self._state is CircuitState.HALF_OPEN:
            self._trial_in_flight = False

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._trial_in_flight = False
        logger.warning(
            "Circuito '%s' abierto por %.0f s tras fallos seguidos del servicio.",
            self.name,
            self._recovery,
        )

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._trial_in_flight = False
        logger.info("Circuito '%s' cerrado: el servicio responde de nuevo.", self.name)
