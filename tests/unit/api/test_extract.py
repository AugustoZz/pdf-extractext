"""
Tests unitarios para el endpoint de extracción de PDF.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.services.extractor import PDFValidationError
from app.services.extractor.models import ExtractedDocument

client = TestClient(app)

@pytest.fixture
def mock_repo():
    with patch("app.api.v1.endpoints.extract.DocumentRepository") as mock:
        yield mock

@pytest.fixture
def mock_service():
    with patch("app.api.v1.endpoints.extract._service") as mock:
        yield mock

def test_extract_pdf_duplicate_checksum(mock_repo, mock_service):
    # Simular que el checksum ya existe en la BD
    mock_service.calculate_checksum.return_value = "fakechecksum123"
    mock_repo.get_by_checksum = AsyncMock(return_value={"id": "existing123"})
    
    response = client.post(
        "/api/v1/extract", 
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")}
    )
    assert response.status_code == 409
    assert "ya existe en la base de datos" in response.json()["detail"]

def test_extract_pdf_success_saves_to_db(mock_repo, mock_service):
    # Simular que el checksum NO existe
    mock_service.calculate_checksum.return_value = "newchecksum123"
    mock_repo.get_by_checksum = AsyncMock(return_value=None)
    
    # Simular la extracción exitosa
    mock_doc = ExtractedDocument(text="Texto", checksum="newchecksum123", page_count=1, metadata={})
    mock_service.extract.return_value = mock_doc
    
    # Simular el guardado en la BD
    saved_doc = {"id": "new123", "text": "Texto", "checksum": "newchecksum123", "page_count": 1, "metadata": {}}
    mock_repo.create = AsyncMock(return_value=saved_doc)

    response = client.post(
        "/api/v1/extract", 
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")}
    )
    
    assert response.status_code == 201
    assert response.json()["id"] == "new123"
    assert response.json()["checksum"] == "newchecksum123"
