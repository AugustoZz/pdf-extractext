"""Consul: descubrimiento del extractor y configuración KV, con Consul simulado."""
import base64

import httpx
import pytest

from app.infrastructure.consul import (
    ConsulServiceResolver,
    NoHealthyInstanceError,
    StaticURLResolver,
    read_kv_config,
)


def _entry(address, port, node_address="10.0.0.1"):
    return {"Node": {"Address": node_address}, "Service": {"Address": address, "Port": port}}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _resolver(handler, **kwargs):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ConsulServiceResolver(
        "http://consul:8500", "extractor", path="/extract", client=client, chooser=lambda urls: urls[0], **kwargs
    )


# ── Descubrimiento ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_static_resolver_returns_its_url():
    assert await StaticURLResolver("http://extractor-lb/extract").resolve() == "http://extractor-lb/extract"


@pytest.mark.asyncio
async def test_asks_consul_only_for_healthy_instances_and_builds_the_url():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[_entry("extractor-lb", 80)])

    resolver = _resolver(handler)
    assert await resolver.resolve() == "http://extractor-lb:80/extract"
    assert requests[0].url.path == "/v1/health/service/extractor"
    assert requests[0].url.params["passing"] == "true"


@pytest.mark.asyncio
async def test_uses_the_node_address_when_the_service_has_none():
    resolver = _resolver(lambda request: httpx.Response(200, json=[_entry("", 8000, node_address="172.18.0.5")]))
    assert await resolver.resolve() == "http://172.18.0.5:8000/extract"


@pytest.mark.asyncio
async def test_caches_instances_to_avoid_a_consul_hop_per_request():
    calls = []
    clock = FakeClock()

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[_entry("extractor-lb", 80)])

    resolver = _resolver(handler, cache_seconds=10, clock=clock)
    await resolver.resolve()
    clock.now = 9
    await resolver.resolve()
    assert len(calls) == 1
    clock.now = 10
    await resolver.resolve()
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_no_healthy_instance_is_an_error_not_a_fallback():
    resolver = _resolver(lambda request: httpx.Response(200, json=[]), fallback_url="http://extractor-lb/extract")
    with pytest.raises(NoHealthyInstanceError):
        await resolver.resolve()


@pytest.mark.asyncio
async def test_consul_down_without_cache_uses_the_fallback_url():
    def handler(request):
        raise httpx.ConnectError("sin consul")

    resolver = _resolver(handler, fallback_url="http://extractor-lb/extract")
    assert await resolver.resolve() == "http://extractor-lb/extract"


@pytest.mark.asyncio
async def test_consul_down_prefers_the_last_known_instances_over_the_fallback():
    clock = FakeClock()
    answers = [httpx.Response(200, json=[_entry("10.0.0.7", 8000)])]

    def handler(request):
        if answers:
            return answers.pop()
        raise httpx.ConnectError("sin consul")

    resolver = _resolver(handler, fallback_url="http://extractor-lb/extract", cache_seconds=10, clock=clock)
    await resolver.resolve()
    clock.now = 60
    assert await resolver.resolve() == "http://10.0.0.7:8000/extract"


@pytest.mark.asyncio
async def test_consul_down_without_cache_or_fallback_is_an_error():
    resolver = _resolver(lambda request: httpx.Response(500))
    with pytest.raises(NoHealthyInstanceError):
        await resolver.resolve()


# ── Configuración KV ─────────────────────────────────────────────


def _kv(key, value):
    encoded = None if value is None else base64.b64encode(value.encode()).decode()
    return {"Key": key, "Value": encoded}


def _kv_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_reads_every_key_under_the_prefix():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[
            _kv("config/pdf-extractext/", None),
            _kv("config/pdf-extractext/EXTRACTOR_TIMEOUT_SECONDS", "45"),
            _kv("config/pdf-extractext/log_level", "DEBUG"),
        ])

    config = read_kv_config("http://consul:8500", "config/pdf-extractext", client=_kv_client(handler))
    assert config == {"EXTRACTOR_TIMEOUT_SECONDS": "45", "LOG_LEVEL": "DEBUG"}
    assert requests[0].url.path == "/v1/kv/config/pdf-extractext/"
    assert "recurse" in requests[0].url.params


def test_ignores_nested_keys():
    def handler(request):
        return httpx.Response(200, json=[_kv("config/pdf-extractext/otro/CLAVE", "x")])

    assert read_kv_config("http://consul:8500", "config/pdf-extractext", client=_kv_client(handler)) == {}


def test_missing_prefix_means_no_config():
    assert read_kv_config(
        "http://consul:8500", "config/pdf-extractext", client=_kv_client(lambda request: httpx.Response(404))
    ) == {}


def test_consul_down_means_no_config_instead_of_crashing():
    def handler(request):
        raise httpx.ConnectError("sin consul")

    assert read_kv_config("http://consul:8500", "config/pdf-extractext", client=_kv_client(handler)) == {}


# ── Settings con Consul ──────────────────────────────────────────

from app.core.config.settings import load_settings  # noqa: E402


def test_settings_ignore_consul_when_disabled(monkeypatch):
    monkeypatch.setenv("CONSUL_ENABLED", "false")
    calls = []
    settings = load_settings(read_kv=lambda *args, **kwargs: calls.append(args) or {})
    assert calls == []
    assert settings.CONSUL_ENABLED is False


def test_consul_values_override_environment_variables(monkeypatch):
    monkeypatch.setenv("CONSUL_ENABLED", "true")
    monkeypatch.setenv("EXTRACTOR_TIMEOUT_SECONDS", "30")
    settings = load_settings(read_kv=lambda *args, **kwargs: {"EXTRACTOR_TIMEOUT_SECONDS": "45"})
    assert settings.EXTRACTOR_TIMEOUT_SECONDS == 45.0


def test_consul_cannot_change_how_to_reach_consul_or_add_unknown_keys(monkeypatch):
    monkeypatch.setenv("CONSUL_ENABLED", "true")
    monkeypatch.setenv("CONSUL_URL", "http://consul:8500")
    settings = load_settings(read_kv=lambda *args, **kwargs: {
        "CONSUL_URL": "http://otro:8500",
        "CONSUL_ENABLED": "false",
        "NO_EXISTE": "x",
    })
    assert settings.CONSUL_URL == "http://consul:8500"
    assert settings.CONSUL_ENABLED is True
    assert not hasattr(settings, "NO_EXISTE")


def test_invalid_value_in_consul_fails_at_startup(monkeypatch):
    monkeypatch.setenv("CONSUL_ENABLED", "true")
    with pytest.raises(ValueError):
        load_settings(read_kv=lambda *args, **kwargs: {"MAX_FILE_SIZE_MB": "-1"})
