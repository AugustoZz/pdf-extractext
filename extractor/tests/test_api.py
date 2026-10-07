"""Tests del contrato HTTP (docs/extractor_contract.md)."""
import pytest
from fastapi.testclient import TestClient

from extractor_service import main
from extractor_service.admission import Admission
from extractor_service.config import settings


@pytest.fixture(scope="module")
def client():
    # Con el context manager corre el lifespan, que crea el pool de procesos.
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def post_pdf(client):
    def post(data: bytes):
        return client.post("/extract", content=data, headers={"Content-Type": "application/pdf"})

    return post


def test_extract_returns_content_and_page_count(post_pdf, text_pdf):
    response = post_pdf(text_pdf)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"content", "page_count"}
    assert "Hola mundo" in body["content"]
    assert body["page_count"] == 1


def test_invalid_pdf_returns_422(post_pdf):
    response = post_pdf(b"esto no es un PDF")

    assert response.status_code == 422
    assert "firma" in response.json()["detail"]


def test_password_protected_pdf_returns_422(post_pdf, password_pdf):
    assert post_pdf(password_pdf).status_code == 422


def test_pdf_over_size_limit_returns_413(monkeypatch, post_pdf, text_pdf):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)

    response = post_pdf(text_pdf + b"\0" * (1024 * 1024))

    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]


def test_pdf_at_size_limit_is_accepted(monkeypatch, post_pdf, text_pdf):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    padding = b"\0" * (1024 * 1024 - len(text_pdf))

    assert post_pdf(text_pdf + padding).status_code == 200


def test_saturated_service_returns_503(monkeypatch, post_pdf, text_pdf):
    # Sin lugares libres: ninguna petición puede entrar.
    monkeypatch.setattr(main, "_admission", Admission(capacity=0, wait_timeout=0.01))

    response = post_pdf(text_pdf)

    assert response.status_code == 503
    assert "saturado" in response.json()["detail"]


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
