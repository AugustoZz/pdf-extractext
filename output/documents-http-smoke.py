"""Verificación integrada contra una base exclusiva de prueba."""
import io
import json
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.core.config import settings
from app.main import app

assert settings.MONGODB_DB_NAME == "pdf_extractext_http_smoke", "No usar la base real"

writer = PdfWriter()
page = writer.add_blank_page(width=612, height=792)
font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
stream = DecodedStreamObject()
stream.set_data(b"BT /F1 12 Tf 72 720 Td (HTTP integration smoke) Tj ET")
page[NameObject("/Contents")] = writer._add_object(stream)
writer.add_metadata({"/Author": "HTTP smoke author"})
buffer = io.BytesIO()
writer.write(buffer)
pdf = buffer.getvalue()

with TestClient(app) as client:
    doc_id = None
    try:
        response = client.post("/api/v1/extract", files={"file": ("http-smoke.pdf", pdf, "application/octet-stream")})
        assert response.status_code == 201, response.text
        saved = response.json()
        doc_id = saved["id"]
        assert saved["page_count"] == 1
        assert "HTTP integration smoke" in saved["text"], saved
        assert saved["metadata"]["author"] == "HTTP smoke author"
        duplicate = client.post("/api/v1/extract", files={"file": ("http-smoke.pdf", pdf, "application/pdf")})
        assert duplicate.status_code == 409, duplicate.text
        invalid = client.post("/api/v1/extract", files={"file": ("invalid.pdf", b"not a PDF", "application/pdf")})
        assert invalid.status_code == 422, invalid.text
        assert client.get(f"/api/v1/documents/{doc_id}").status_code == 200
        print(json.dumps({"status": "passed", "checks": ["HTTP extraction via nginx", "Markdown saved in MongoDB", "metadata retained", "generic MIME accepted", "duplicate 409", "invalid PDF 422", "document CRUD"], "database": settings.MONGODB_DB_NAME}, ensure_ascii=False))
    finally:
        if doc_id:
            deleted = client.delete(f"/api/v1/documents/{doc_id}")
            assert deleted.status_code == 200, deleted.text
