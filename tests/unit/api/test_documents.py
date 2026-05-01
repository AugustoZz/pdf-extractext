"""
Tests unitarios para los endpoints CRUD de documentos.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_repo():
    with patch("app.api.v1.endpoints.documents.DocumentRepository") as mock:
        yield mock

def test_list_documents_empty(mock_repo):
    mock_repo.get_all = AsyncMock(return_value=[])
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert response.json() == {"data": []}

def test_get_document_not_found(mock_repo):
    mock_repo.get_by_id = AsyncMock(return_value=None)
    response = client.get("/api/v1/documents/12345")
    assert response.status_code == 404

def test_get_document_success(mock_repo):
    mock_doc = {"id": "12345", "text": "Hola", "checksum": "abc"}
    mock_repo.get_by_id = AsyncMock(return_value=mock_doc)
    response = client.get("/api/v1/documents/12345")
    assert response.status_code == 200
    assert response.json() == mock_doc

def test_delete_document_success(mock_repo):
    mock_repo.delete = AsyncMock(return_value=True)
    response = client.delete("/api/v1/documents/12345")
    assert response.status_code == 200

def test_update_document_success(mock_repo):
    mock_doc = {"id": "12345", "text": "Actualizado"}
    mock_repo.update = AsyncMock(return_value=mock_doc)
    response = client.put("/api/v1/documents/12345", json={"text": "Actualizado"})
    assert response.status_code == 200
    assert response.json() == mock_doc
