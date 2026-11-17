"""Circuit breaker: estados, transiciones y reloj inyectado (sin dormir)."""
import pytest

from app.services.resilience import CircuitBreaker, CircuitOpenError, CircuitState


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _breaker(clock, threshold=3, recovery=30.0):
    return CircuitBreaker("extractor", failure_threshold=threshold, recovery_timeout=recovery, clock=clock)


def _fail(breaker, times):
    for _ in range(times):
        breaker.before_call()
        breaker.record_failure()


def test_starts_closed_and_lets_calls_through():
    breaker = _breaker(FakeClock())
    breaker.before_call()
    assert breaker.state is CircuitState.CLOSED


def test_opens_after_consecutive_failures_reach_the_threshold():
    breaker = _breaker(FakeClock(), threshold=3)
    _fail(breaker, 2)
    assert breaker.state is CircuitState.CLOSED
    _fail(breaker, 1)
    assert breaker.state is CircuitState.OPEN


def test_a_success_resets_the_failure_count():
    breaker = _breaker(FakeClock(), threshold=3)
    _fail(breaker, 2)
    breaker.before_call()
    breaker.record_success()
    _fail(breaker, 2)
    assert breaker.state is CircuitState.CLOSED


def test_open_circuit_rejects_without_calling_and_says_when_to_retry():
    clock = FakeClock()
    breaker = _breaker(clock, threshold=1, recovery=30.0)
    _fail(breaker, 1)
    clock.advance(10)
    with pytest.raises(CircuitOpenError) as exc_info:
        breaker.before_call()
    assert exc_info.value.retry_after == pytest.approx(20.0)


def test_after_recovery_timeout_lets_a_single_trial_call_through():
    clock = FakeClock()
    breaker = _breaker(clock, threshold=1, recovery=30.0)
    _fail(breaker, 1)
    clock.advance(30)
    breaker.before_call()
    assert breaker.state is CircuitState.HALF_OPEN
    # Mientras la prueba está en curso, el resto sigue rechazado.
    with pytest.raises(CircuitOpenError):
        breaker.before_call()


def test_successful_trial_closes_the_circuit():
    clock = FakeClock()
    breaker = _breaker(clock, threshold=1)
    _fail(breaker, 1)
    clock.advance(30)
    breaker.before_call()
    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    breaker.before_call()


def test_failed_trial_opens_the_circuit_again_for_a_full_timeout():
    clock = FakeClock()
    breaker = _breaker(clock, threshold=3, recovery=30.0)
    _fail(breaker, 3)
    clock.advance(30)
    breaker.before_call()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    clock.advance(29)
    with pytest.raises(CircuitOpenError):
        breaker.before_call()


def test_released_trial_lets_the_next_call_try_again():
    """Si la prueba se cancela (el cliente cortó), no debe quedar trabado en semiabierto."""
    clock = FakeClock()
    breaker = _breaker(clock, threshold=1)
    _fail(breaker, 1)
    clock.advance(30)
    breaker.before_call()
    breaker.release()
    breaker.before_call()
    assert breaker.state is CircuitState.HALF_OPEN


def test_results_of_calls_started_before_opening_do_not_change_an_open_circuit():
    clock = FakeClock()
    breaker = _breaker(clock, threshold=1, recovery=30.0)
    breaker.before_call()  # llamada lenta que empezó con el circuito cerrado
    _fail(breaker, 1)
    breaker.record_success()  # termina tarde: no cierra el circuito
    assert breaker.state is CircuitState.OPEN


@pytest.mark.parametrize("threshold,recovery", [(0, 30.0), (3, 0.0)])
def test_rejects_invalid_configuration(threshold, recovery):
    with pytest.raises(ValueError):
        CircuitBreaker("extractor", failure_threshold=threshold, recovery_timeout=recovery)
