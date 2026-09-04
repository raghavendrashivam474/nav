"""S9 PDF Retrieval tests — deterministic unit tests.

Validates PDF extraction, size limits, corrupted PDF handling,
and password-protected PDF handling.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import pypdf
import pytest

from capabilities.research.retrieval import (
    HttpxRetriever,
    extract_text_from_pdf_bytes,
)
from core.contracts.research import ResearchSource, SourceStatus


class TestPdfExtraction:
    def test_extracts_text_from_valid_pdf_mock(self) -> None:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Solid-state electrolyte ionic transport mechanism."

        with pytest.MonkeyPatch.context() as mp:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False
            mock_reader.pages = [mock_page]
            mp.setattr("pypdf.PdfReader", lambda _: mock_reader)

            text, truncated = extract_text_from_pdf_bytes(b"%PDF-1.4 mock", max_chars=1000)
            assert "Solid-state electrolyte ionic transport" in text
            assert truncated is False

    def test_handles_empty_page_pdf(self) -> None:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        raw_bytes = buf.getvalue()

        with pytest.raises(ValueError, match="no extractable text"):
            extract_text_from_pdf_bytes(raw_bytes, max_chars=1000)

    def test_handles_corrupted_pdf_bytes(self) -> None:
        corrupted_bytes = b"%PDF-1.4 invalid garbage bytes here"
        with pytest.raises(ValueError, match="Malformed or unreadable PDF"):
            extract_text_from_pdf_bytes(corrupted_bytes, max_chars=1000)

    def test_truncates_at_max_chars(self) -> None:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "A" * 500

        with pytest.MonkeyPatch.context() as mp:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False
            mock_reader.pages = [mock_page, mock_page]
            mp.setattr("pypdf.PdfReader", lambda _: mock_reader)

            text, truncated = extract_text_from_pdf_bytes(b"%PDF-fake", max_chars=300)
            assert len(text) == 300
            assert truncated is True

    def test_handles_encrypted_pdf(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.decrypt.side_effect = Exception("Password required")
            mp.setattr("pypdf.PdfReader", lambda _: mock_reader)

            with pytest.raises(ValueError, match="password-protected"):
                extract_text_from_pdf_bytes(b"%PDF-fake", max_chars=1000)


class TestHttpxRetrieverPdfRouting:
    def test_httpx_retriever_dispatches_pdf(self, monkeypatch) -> None:
        source = ResearchSource(
            source_id="src_pdf_1",
            url="https://arxiv.org/pdf/2401.00001.pdf",
            canonical_url="https://arxiv.org/pdf/2401.00001.pdf",
            title="ArXiv Paper",
            status=SourceStatus.DISCOVERED,
        )

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.iter_bytes.return_value = [b"%PDF-1.4 header", b" stream content"]
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.stream.return_value.__enter__.return_value = mock_response
        mock_client.stream.return_value.__exit__.return_value = False

        monkeypatch.setattr("httpx.Client", lambda **kwargs: mock_client)
        monkeypatch.setattr(
            "capabilities.research.retrieval.extract_text_from_pdf_bytes",
            lambda b, m: ("Extracted paper abstract and findings.", False),
        )

        retriever = HttpxRetriever()
        content = retriever.retrieve(source, max_chars=5000, timeout=10.0)

        assert content.source_id == "src_pdf_1"
        assert content.content_type == "application/pdf"
        assert "Extracted paper abstract" in content.text
        assert content.truncated is False
