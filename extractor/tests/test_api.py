"""Tests del contrato HTTP (docs/extractor_contract.md)."""
import pytest
from fastapi.testclient import TestClient

from extractor_service.config import settings
from extractor_service.main import app

client = TestClient(app)


def post_pdf(data: bytes):
    return client.post("/extract", content=data, headers={"Content-Type": "application/pdf"})


def test_extract_returns_content_and_page_count(text_pdf):
    response = post_pdf(text_pdf)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"content", "page_count"}
    assert "Hola mundo" in body["content"]
    assert body["page_count"] == 1


def test_invalid_pdf_returns_422():
    response = post_pdf(b"esto no es un PDF")

    assert response.status_code == 422
    assert "firma" in response.json()["detail"]


def test_password_protected_pdf_returns_422(password_pdf):
    assert post_pdf(password_pdf).status_code == 422


def test_pdf_over_size_limit_returns_413(monkeypatch, text_pdf):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)

    response = post_pdf(text_pdf + b"\0" * (1024 * 1024))

    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]


def test_pdf_at_size_limit_is_accepted(monkeypatch, text_pdf):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    padding = b"\0" * (1024 * 1024 - len(text_pdf))

    assert post_pdf(text_pdf + padding).status_code == 200


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
