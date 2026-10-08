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
