"""Contrato HTTP y errores del extractor externo; no requiere Docker/Mongo."""
import httpx
import pytest
from unittest.mock import MagicMock

from app.services.extractor import PDFValidationError, PDFTooLargeError
from app.services.extractor.http_extractor import HTTPPDFExtractorService, ExtractorHTTPError


@pytest.mark.asyncio
async def test_posts_binary_pdf_and_maps_markdown_without_extracting_text():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"content": "# Título\n\n**Texto**", "page_count": 2})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        service._metadata_reader = MagicMock()
        service._metadata_reader.extract_metadata.return_value = {"author": "Autor"}
        result = await service.extract(b"%PDF-test")

    assert requests[0].url == httpx.URL("http://extractor/extract")
    assert requests[0].headers["content-type"] == "application/pdf"
    assert requests[0].content == b"%PDF-test"
    assert result.text == "# Título\n\n**Texto**"
    assert result.page_count == 2
    assert result.metadata == {"author": "Autor"}
    service._metadata_reader.extract_text.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,error", [(422, PDFValidationError), (413, PDFTooLargeError), (503, ExtractorHTTPError), (500, ExtractorHTTPError)])
async def test_remote_errors_are_not_saved_as_success(status, error):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(error):
            await service.extract(b"%PDF-test")


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.ReadTimeout("timeout")])
async def test_connection_errors_return_unavailable(error):
    def handler(request):
        raise error
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(ExtractorHTTPError) as exc:
            await service.extract(b"%PDF-test")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"content": None, "page_count": 1}, {"content": "", "page_count": True}, {"content": "", "page_count": 0}, {"content": "", "page_count": -1}, {"content": "", "page_count": "1"}])
async def test_invalid_success_payload_is_bad_gateway(payload):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(ExtractorHTTPError) as exc:
            await service.extract(b"%PDF-test")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_metadata_failure_does_not_fail_remote_extraction():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"content": "Texto", "page_count": 1}))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        service._metadata_reader = MagicMock()
        service._metadata_reader.extract_metadata.side_effect = ValueError("invalid metadata")
        result = await service.extract(b"%PDF-test")
    assert result.text == "Texto"
    assert result.metadata == {}


@pytest.mark.asyncio
async def test_invalid_pdf_header_never_contacts_extractor():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: pytest.fail("unexpected HTTP request"))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(PDFValidationError):
            await service.extract(b"not a pdf")


@pytest.mark.asyncio
async def test_without_metadata_does_not_reread_the_pdf():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"content": "Texto", "page_count": 1}))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        service._metadata_reader = MagicMock()
        result = await service.extract(b"%PDF-test", with_metadata=False)
    assert result.text == "Texto"
    assert result.metadata == {}
    service._metadata_reader.extract_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_validation_error_keeps_the_extractor_detail():
    detail = "El archivo PDF está protegido con contraseña y no se puede procesar."
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(422, json={"detail": detail}))) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(PDFValidationError, match="contraseña"):
            await service.extract(b"%PDF-test")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [httpx.Response(422), httpx.Response(422, json=["no es un dict"]), httpx.Response(422, json={"detail": ["lista"]})])
async def test_validation_error_without_usable_detail_uses_generic_message(response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
        service = HTTPPDFExtractorService("http://extractor/extract", client=client)
        with pytest.raises(PDFValidationError, match="inválido"):
            await service.extract(b"%PDF-test")


# ── Circuit breaker y descubrimiento ─────────────────────────────

import asyncio  # noqa: E402

from app.infrastructure.consul import NoHealthyInstanceError, StaticURLResolver  # noqa: E402
from app.services.resilience import CircuitBreaker, CircuitState  # noqa: E402

_OK = {"content": "Texto", "page_count": 1}


def _service_with(handler, breaker, resolver=None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HTTPPDFExtractorService(
        "http://extractor/extract", client=client, breaker=breaker, resolver=resolver
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [
    lambda request: (_ for _ in ()).throw(httpx.ConnectError("caído")),
    lambda request: httpx.Response(503),
    lambda request: httpx.Response(500),
    lambda request: httpx.Response(200, json={"content": 1}),
])
async def test_extractor_failures_open_the_circuit(failure):
    breaker = CircuitBreaker("extractor", failure_threshold=2)
    service = _service_with(failure, breaker)
    for _ in range(2):
        with pytest.raises(ExtractorHTTPError):
            await service.extract(b"%PDF-test", with_metadata=False)
    assert breaker.state is CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_circuit_answers_503_without_calling_the_extractor():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    breaker = CircuitBreaker("extractor", failure_threshold=1, recovery_timeout=30)
    service = _service_with(handler, breaker)
    with pytest.raises(ExtractorHTTPError):
        await service.extract(b"%PDF-test", with_metadata=False)
    with pytest.raises(ExtractorHTTPError) as exc_info:
        await service.extract(b"%PDF-test", with_metadata=False)
    assert len(calls) == 1
    assert exc_info.value.status_code == 503
    assert exc_info.value.retry_after is not None and exc_info.value.retry_after > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [422, 413])
async def test_invalid_pdfs_do_not_count_as_extractor_failures(status):
    breaker = CircuitBreaker("extractor", failure_threshold=1)
    service = _service_with(lambda request: httpx.Response(status), breaker)
    with pytest.raises((PDFValidationError, PDFTooLargeError)):
        await service.extract(b"%PDF-test", with_metadata=False)
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_local_validation_does_not_touch_the_circuit():
    breaker = CircuitBreaker("extractor", failure_threshold=1)
    service = _service_with(lambda request: httpx.Response(200, json=_OK), breaker)
    with pytest.raises(PDFValidationError):
        await service.extract(b"no es pdf", with_metadata=False)
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_cancelled_trial_does_not_leave_the_circuit_stuck():
    clock = [0.0]
    breaker = CircuitBreaker("extractor", failure_threshold=1, recovery_timeout=30, clock=lambda: clock[0])
    breaker.before_call()
    breaker.record_failure()
    clock[0] = 30
    started = asyncio.Event()

    async def slow_handler(request):
        started.set()
        await asyncio.sleep(10)
        return httpx.Response(200, json=_OK)

    service = _service_with(slow_handler, breaker)
    task = asyncio.create_task(service.extract(b"%PDF-test", with_metadata=False))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    service = _service_with(lambda request: httpx.Response(200, json=_OK), breaker)
    result = await service.extract(b"%PDF-test", with_metadata=False)
    assert result.text == "Texto"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_posts_to_the_url_the_resolver_returns():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json=_OK)

    service = _service_with(
        handler, CircuitBreaker("extractor"), StaticURLResolver("http://10.0.0.7:8000/extract")
    )
    await service.extract(b"%PDF-test", with_metadata=False)
    assert seen == ["http://10.0.0.7:8000/extract"]


@pytest.mark.asyncio
async def test_no_healthy_instance_is_a_503_and_counts_as_failure():
    class NoInstances:
        async def start(self): pass
        async def close(self): pass
        async def resolve(self):
            raise NoHealthyInstanceError("sin instancias")

    breaker = CircuitBreaker("extractor", failure_threshold=1)
    service = _service_with(lambda request: httpx.Response(200, json=_OK), breaker, NoInstances())
    with pytest.raises(ExtractorHTTPError) as exc_info:
        await service.extract(b"%PDF-test", with_metadata=False)
    assert exc_info.value.status_code == 503
    assert breaker.state is CircuitState.OPEN
