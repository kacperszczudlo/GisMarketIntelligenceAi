from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.parsing.converter import DocumentParsingEngine


def test_converter_sanitizes_markdown_and_cleans_memory(tmp_path: Path):
    mock_pdf = tmp_path / "test_doc.pdf"
    mock_pdf.write_bytes(b"%PDF-1.4 dummy content")

    raw_docling_md = (
        "# Rozdział 1\n\n"
        "| Kryterium | Waga |\n"
        "|---|---|\n"
        "| | |\n"
        "| Cena | 60% |\n"
    )

    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = raw_docling_md

    mock_result = MagicMock()
    mock_result.document = mock_doc

    engine = DocumentParsingEngine()

    with patch.object(engine, "_convert_pdf", return_value=mock_result):
        with patch("gc.collect") as mock_gc:
            output_md = engine.convert_to_markdown(mock_pdf)

            assert "| Cena | 60% |" in output_md
            assert "| | |" not in output_md
            assert mock_gc.called
