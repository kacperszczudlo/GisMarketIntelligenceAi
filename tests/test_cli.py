from pathlib import Path
from typing import Any, List
import uuid
import pytest
from pytest_mock import MockerFixture
from src.cli import (
    _ensure_attachment_record,
    _lookup_procurement_metadata,
    _run_analyze,
    _run_index,
    _run_ingest,
    _run_parse,
    create_cli_parser,
    ensure_sample_swz_pdf,
    main,
)
from src.evaluation.ragas_guard import EvaluationResult
from src.inference.models import TenderReport
from src.ingestion.models import TenderNotice

EXIT_CODE_SUCCESS = 0
EXIT_CODE_ERROR = 1
DEFAULT_INGEST_LIMIT = 5
MIN_FAITHFULNESS_THRESHOLD = 0.95


@pytest.mark.parametrize(
    ("cli_args", "expected_command", "expected_attr", "expected_val"),
    [
        (["analyze", "--ocds-id", "OCDS-987654"], "analyze", "ocds_id", "OCDS-987654"),
        (["analyze", "--ocds-id", "OCDS-12345", "--output", "raport.md"], "analyze", "output", "raport.md"),
        (["ingest", "--cpv", "72220000-3", "--limit", "5"], "ingest", "limit", DEFAULT_INGEST_LIMIT),
        (["parse", "--input-dir", "data_raw", "--output-dir", "data_processed"], "parse", "input_dir", "data_raw"),
        (["index", "--procurement-id", "PROC-123"], "index", "procurement_id", "PROC-123"),
    ],
    ids=["analyze_basic", "analyze_with_output", "ingest_cpv_limit", "parse_dirs", "index_proc_id"],
)
def test_should_parse_cli_subcommands_and_options_correctly(
    cli_args: List[str],
    expected_command: str,
    expected_attr: str,
    expected_val: object,
) -> None:
    # Arrange
    parser = create_cli_parser()

    # Act
    args = parser.parse_args(cli_args)

    # Assert
    assert args.command == expected_command
    assert getattr(args, expected_attr) == expected_val


def test_should_exit_when_cli_invoked_without_subcommand_or_required_args() -> None:
    # Arrange
    parser = create_cli_parser()

    # Act & Assert
    with pytest.raises(SystemExit):
        parser.parse_args([])

    with pytest.raises(SystemExit):
        main(["analyze"])


def test_should_exit_cleanly_with_zero_when_help_flag_is_passed() -> None:
    # Arrange & Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == EXIT_CODE_SUCCESS


def test_should_return_zero_when_parsing_empty_input_directory(tmp_path: Path) -> None:
    # Arrange
    input_dir = tmp_path / "empty_input"
    output_dir = tmp_path / "empty_output"
    input_dir.mkdir()
    output_dir.mkdir()

    # Act
    exit_code = main(["parse", "--input-dir", str(input_dir), "--output-dir", str(output_dir)])

    # Assert
    assert exit_code == EXIT_CODE_SUCCESS


def test_should_convert_all_pdfs_in_directory_during_parse_command(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    in_dir = tmp_path / "raw"
    out_dir = tmp_path / "proc"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "doc1.pdf").write_bytes(b"%PDF-1.4")

    mock_engine = mocker.MagicMock()
    mock_engine.convert_to_markdown.return_value = "# Parsed"
    mocker.patch("src.parsing.converter.DocumentParsingEngine", return_value=mock_engine)

    # Act
    code = _run_parse(str(in_dir), str(out_dir))

    # Assert
    assert code == EXIT_CODE_SUCCESS
    mock_engine.convert_to_markdown.assert_called_once()


def test_should_generate_valid_sample_swz_pdf_with_domain_keywords(tmp_path: Path) -> None:
    # Arrange & Act
    pdf_path = ensure_sample_swz_pdf(tmp_path)
    second_call_path = ensure_sample_swz_pdf(tmp_path)

    # Assert
    assert pdf_path.exists()
    assert second_call_path == pdf_path
    raw_bytes = pdf_path.read_bytes()
    assert raw_bytes.startswith(b"%PDF-1.4")
    assert b"EWMAPA" in raw_bytes
    assert b".str" in raw_bytes


@pytest.mark.asyncio
async def test_should_ingest_notices_and_save_to_database(
    sample_tender_notice: TenderNotice,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.chdir(tmp_path)
    mock_client = mocker.MagicMock()
    mock_client.fetch_notices = mocker.AsyncMock(return_value=[sample_tender_notice])
    mocker.patch("src.ingestion.client.EZamowieniaClient", return_value=mock_client)

    # Act
    code = await _run_ingest(cpv="72220000-3", limit=1, download_attachments=False)

    # Assert
    assert code == EXIT_CODE_SUCCESS
    assert mock_client.save_notice_to_db.call_count == 2
    assert (tmp_path / "data_processed" / "SWZ_Niepolomice.md").exists()


def test_should_ensure_attachment_record_and_index_markdown_files(
    tmp_path: Path,
    mocker: MockerFixture,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    md_dir = tmp_path / "md"
    md_dir.mkdir()
    (md_dir / "SWZ_Niepolomice.md").write_text("# Rozdział I\nTreść SWZ.", encoding="utf-8")
    (md_dir / "empty.md").write_text("   ", encoding="utf-8")

    proc_uuid = uuid.uuid4()
    att_uuid = uuid.uuid4()
    mock_db_cursor.fetchone.side_effect = [(str(proc_uuid),), (str(att_uuid),)]

    mock_indexer = mocker.MagicMock()
    mock_indexer.index_document.return_value = 4
    mocker.patch("src.indexing.indexer.DatabaseIndexer", return_value=mock_indexer)
    mocker.patch("src.indexing.embedder.BgeM3Embedder")

    # Act
    code = _run_index(procurement_id="ocds-148610-niepolomice", markdown_dir=str(md_dir))

    # Assert
    assert code == EXIT_CODE_SUCCESS
    mock_indexer.index_document.assert_called_once()


def test_should_lookup_procurement_metadata_with_database_and_fallback(
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_db_cursor.fetchone.return_value = (
        "ocds-148610-niepolomice",
        "Modernizacja BDOT500",
        "Gmina Niepołomice",
    )

    # Act
    resolved_id, title, municipality = _lookup_procurement_metadata("ocds-148610-niepolomice")

    # Assert
    assert resolved_id == "ocds-148610-niepolomice"
    assert title == "Modernizacja BDOT500"
    assert municipality == "Gmina Niepołomice"


@pytest.mark.asyncio
async def test_should_run_analyze_enforce_grounding_fallback_and_write_report(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    out_file = tmp_path / "raport_out.md"
    mocker.patch(
        "src.cli._lookup_procurement_metadata",
        return_value=("ocds-148610-niepolomice", "Modernizacja BDOT500", "Gmina Niepołomice"),
    )

    mock_pipeline = mocker.MagicMock()
    mock_pipeline.retrieve.return_value = [
        {"content": "1. Przedmiotem zamówienia jest modernizacja bazy danych BDOT500 oraz inicjalizacja GESUT."}
    ]
    mocker.patch("src.retrieval.pipeline.RetrievalPipeline", return_value=mock_pipeline)

    fake_report = TenderReport(
        procurement_id="ocds-148610-niepolomice",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        executive_summary="Podsumowanie",
        markdown_report="# Raport\nTreść raportu",
    )
    mock_gen = mocker.MagicMock()
    mock_gen.generate = mocker.AsyncMock(return_value=fake_report)
    mock_gen._build_grounded_synthesis.return_value = "### 1. Podsumowanie\nZsyntetyzowany tekst."
    mock_gen._extract_section.return_value = "Zsyntetyzowany tekst."
    mock_gen._extract_citations.return_value = ["SWZ Rozdział I"]
    mocker.patch("src.inference.report_generator.TenderReportGenerator", return_value=mock_gen)

    mock_guard = mocker.MagicMock()
    mock_guard.evaluate_claims_grounding.side_effect = [
        EvaluationResult(faithfulness=0.60, passed=False, reason="Halucynacja"),
        EvaluationResult(faithfulness=1.00, passed=True),
    ]
    mocker.patch("src.evaluation.ragas_guard.RagasGuard", return_value=mock_guard)

    # Act
    code = await _run_analyze(
        ocds_id="ocds-148610-niepolomice",
        query="Jaki jest zakres?",
        output=str(out_file),
        min_faithfulness=MIN_FAITHFULNESS_THRESHOLD,
    )

    # Assert
    assert code == EXIT_CODE_SUCCESS
    assert out_file.exists()
    mock_gen._build_grounded_synthesis.assert_called_once()


def test_should_dispatch_subcommands_and_handle_unexpected_errors_gracefully(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_index = mocker.patch("src.cli._run_index", return_value=EXIT_CODE_SUCCESS)

    # Act
    ok_code = main(["index", "--procurement-id", "OCDS-1"])
    mock_index.side_effect = RuntimeError("Database connection error")
    err_code = main(["index", "--procurement-id", "OCDS-1"])

    # Assert
    assert ok_code == EXIT_CODE_SUCCESS
    assert err_code == EXIT_CODE_ERROR


@pytest.mark.parametrize(
    "file_name",
    [
        "BZP_ocds-148610-custom.md",
        "SWZ_Kornik.md",
        "SWZ_Piaseczno.md",
    ],
    ids=["bzp_prefix", "kornik_stem", "piaseczno_stem"],
)
def test_should_infer_procurement_ocds_and_insert_fallback_when_db_has_no_rows(
    file_name: str,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_db_cursor.fetchone.side_effect = [None, None, None]

    # Act
    att_uuid = _ensure_attachment_record(file_name, "# Treść SWZ", procurement_ocds=None)

    # Assert
    assert isinstance(att_uuid, uuid.UUID)
    assert mock_db_cursor.execute.call_count == 5


def test_should_fallback_to_default_metadata_when_lookup_raises_database_error(
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_db_cursor.execute.side_effect = RuntimeError("DB offline")

    # Act
    resolved_id, title, municipality = _lookup_procurement_metadata("sample")

    # Assert
    assert resolved_id == "sample"
    assert "sample" in title
    assert "Niepołomicach" in municipality


def test_should_raise_value_error_when_explicit_ocds_id_not_found(mock_db_cursor: Any) -> None:
    mock_db_cursor.fetchone.return_value = None
    with pytest.raises(ValueError, match="Nie znaleziono"):
        _lookup_procurement_metadata("ocds-does-not-exist-999")

