"""Tests de la extracción de texto, independientes de HTTP."""
import pytest

from extractor_service.pdf_extractor import PDFValidationError, extract
from tests.pdf_factory import build_pdf


class TestExtract:
    def test_extracts_text_and_page_count(self, text_pdf):
        result = extract(text_pdf)

        assert "Hola mundo" in result.content
        assert result.page_count == 1

    def test_extracts_every_page(self):
        result = extract(build_pdf("Primera", "Segunda", "Tercera"))

        assert result.page_count == 3
        for text in ("Primera", "Segunda", "Tercera"):
            assert text in result.content

    def test_bold_text_is_marked_as_bold(self):
        result = extract(build_pdf("Texto importante", font="Helvetica-Bold"))

        assert "**Texto importante**" in result.content

    def test_text_larger_than_the_body_becomes_a_heading(self):
        pdf = build_pdf("Titulo", "Subtitulo", "Cuerpo", "Mas cuerpo", sizes=(24, 15, 12, 12))

        lines = extract(pdf).content.split("\n\n")

        assert lines[:4] == ["# Titulo", "## Subtitulo", "Cuerpo", "Mas cuerpo"]

    def test_pdf_without_selectable_text_returns_empty_content(self, blank_pdf):
        result = extract(blank_pdf)

        assert result.content == ""
        assert result.page_count == 1

    def test_accepts_pdf_with_owner_restrictions_only(self, owner_restricted_pdf):
        assert extract(owner_restricted_pdf).page_count == 1


class TestValidation:
    @pytest.mark.parametrize("data", [b"", b"esto no es un PDF"])
    def test_rejects_data_without_pdf_signature(self, data):
        with pytest.raises(PDFValidationError, match="firma"):
            extract(data)

    def test_rejects_corrupt_pdf(self):
        with pytest.raises(PDFValidationError, match="corrupto"):
            extract(b"%PDF-1.4\n%contenido roto")

    def test_rejects_password_protected_pdf(self, password_pdf):
        with pytest.raises(PDFValidationError, match="contraseña"):
            extract(password_pdf)
