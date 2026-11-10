from pathlib import Path
import pytest
from pytest_mock import MockerFixture
from docling.datamodel.pipeline_options import TableFormerMode
from src.parsing.config import get_docling_pipeline_options
from src.parsing.converter import DocumentParsingEngine


def test_should_configure_docling_pipeline_options_with_accurate_table_former() -> None:
    # Arrange & Act
    options = get_docling_pipeline_options(do_ocr=False, accurate_tables=True)

    # Assert
    assert options.do_table_structure is True
    assert options.table_structure_options.mode == TableFormerMode.ACCURATE
    assert options.do_ocr is False


def test_should_sanitize_markdown_save_to_disk_and_trigger_gc_cleanup(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    pdf_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"
    pdf_dir.mkdir()
    mock_pdf = pdf_dir / "test_doc.pdf"
    mock_pdf.write_bytes(b"%PDF-1.4 dummy content")

    raw_docling_md = (
        "# Rozdział 1\n\n"
        "| Kryterium | Waga |\n"
        "|---|---|\n"
        "| | |\n"
        "| Cena | 60% |\n"
    )

    mock_doc = mocker.MagicMock()
    mock_doc.export_to_markdown.return_value = raw_docling_md
    mock_result = mocker.MagicMock()
    mock_result.document = mock_doc

    engine = DocumentParsingEngine(output_dir=out_dir)
    mocker.patch.object(engine, "_convert_pdf", return_value=mock_result)
    mock_gc = mocker.patch("src.parsing.converter.gc.collect")

    # Act
    output_md = engine.convert_to_markdown(mock_pdf, save_to_disk=True, do_ocr=False)

    # Assert
    assert "| Cena | 60% |" in output_md
    assert "| | |" not in output_md
    saved_file = out_dir / "test_doc.md"
    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == output_md
    mock_gc.assert_called_once()


def test_should_not_write_file_when_save_to_disk_is_disabled(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_pdf = tmp_path / "in_memory.pdf"
    mock_pdf.write_bytes(b"%PDF-1.4 dummy")
    out_dir = tmp_path / "out"

    mock_result = mocker.MagicMock()
    mock_result.document.export_to_markdown.return_value = "# Tylko w pamięci"

    engine = DocumentParsingEngine(output_dir=out_dir)
    mocker.patch.object(engine, "_convert_pdf", return_value=mock_result)

    # Act
    result = engine.convert_to_markdown(mock_pdf, save_to_disk=False)

    # Assert
    assert result == "# Tylko w pamięci"
    assert not (out_dir / "in_memory.md").exists()


def test_should_raise_file_not_found_error_when_pdf_does_not_exist(
    tmp_path: Path,
) -> None:
    # Arrange
    engine = DocumentParsingEngine(output_dir=tmp_path)
    missing_pdf = tmp_path / "nieistniejacy.pdf"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="PDF file does not exist"):
        engine.convert_to_markdown(missing_pdf)


def test_should_run_garbage_collection_even_when_docling_conversion_fails(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_pdf = tmp_path / "corrupted.pdf"
    mock_pdf.write_bytes(b"%PDF-1.4 broken")

    engine = DocumentParsingEngine(output_dir=tmp_path)
    mocker.patch.object(engine, "_convert_pdf", side_effect=RuntimeError("Docling parse failure"))
    mock_gc = mocker.patch("src.parsing.converter.gc.collect")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Docling parse failure"):
        engine.convert_to_markdown(mock_pdf)

    mock_gc.assert_called_once()
