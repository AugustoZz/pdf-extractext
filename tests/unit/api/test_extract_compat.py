"""Tests del alias POST /extract compatible con el TP de carga y estrés."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.extractor import PDFTooLargeError, PDFValidationError
from app.services.extractor.http_extractor import ExtractorHTTPError
from app.services.extractor.models import ExtractedDocument

client = TestClient(app)


@pytest.fixture
def mock_service():
    with patch("app.api.v1.endpoints.extract._service") as mock:
        mock.extract = AsyncMock()
        yield mock


@pytest.fixture
def mock_repo():
    with patch("app.api.v1.endpoints.extract.DocumentRepository") as mock:
        yield mock


def test_extract_compat_raw_binary_returns_contract(mock_service, mock_repo):
    """El body binario directo es el formato que usan los scripts de la cátedra."""
    mock_service.extract.return_value = ExtractedDocument(
        text="# Título\n\nTexto", page_count=3, metadata={}
    )

    response = client.post(
        "/extract",
        content=b"%PDF-1.4...",
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 200
    assert response.json() == {"content": "# Título\n\nTexto", "page_count": 3}
    # El alias no persiste: el CRUD sigue en /api/v1/extract.
    mock_repo.create.assert_not_called()
    # Ni lee metadatos: no los devuelve y releer el PDF es CPU de la API.
    mock_service.extract.assert_awaited_once_with(b"%PDF-1.4...", with_metadata=False)


def test_extract_compat_multipart_returns_contract(mock_service, mock_repo):
    mock_service.extract.return_value = ExtractedDocument(
        text="Texto", page_count=1, metadata={}
    )

    response = client.post(
        "/extract",
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {"content": "Texto", "page_count": 1}
    mock_repo.create.assert_not_called()


def test_extract_compat_multipart_requires_pdf_extension(mock_service):
    response = client.post(
        "/extract",
        files={"file": ("malicioso.exe", b"MZ\x90\x00", "application/pdf")},
    )

    assert response.status_code == 400
    mock_service.extract.assert_not_awaited()


def test_extract_compat_multipart_requires_file_field(mock_service):
    response = client.post(
        "/extract",
        files={"otro": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
    )

    assert response.status_code == 400
    mock_service.extract.assert_not_awaited()


@pytest.mark.parametrize(
    "error,status",
    [
        (PDFValidationError("PDF inválido"), 422),
        (PDFTooLargeError("PDF demasiado grande"), 413),
        (ExtractorHTTPError("Extractor saturado"), 503),
        (ExtractorHTTPError("Respuesta inválida", 502), 502),
    ],
)
def test_extract_compat_maps_upstream_errors(mock_service, error, status):
    mock_service.extract.side_effect = error

    response = client.post(
        "/extract",
        content=b"%PDF-1.4...",
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == status


def test_extract_compat_rejects_oversized_raw_body(mock_service):
    with patch("app.api.v1.endpoints.extract._MAX_FILE_BYTES", 4):
        response = client.post(
            "/extract",
            content=b"%PDF-1.4...",
            headers={"Content-Type": "application/pdf"},
        )

    assert response.status_code == 413
    mock_service.extract.assert_not_awaited()
