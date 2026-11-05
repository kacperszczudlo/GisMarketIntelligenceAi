import pytest
from src.cli import create_cli_parser


def test_cli_parser_arguments():
    parser = create_cli_parser()
    args = parser.parse_args(["analyze", "--ocds-id", "OCDS-987654"])
    assert args.command == "analyze"
    assert args.ocds_id == "OCDS-987654"


def test_cli_analyze_command_arguments():
    parser = create_cli_parser()
    args = parser.parse_args(["analyze", "--ocds-id", "OCDS-12345", "--output", "raport.md"])
    assert args.command == "analyze"
    assert args.ocds_id == "OCDS-12345"
    assert args.output == "raport.md"


def test_cli_ingest_command_arguments():
    parser = create_cli_parser()
    args = parser.parse_args(["ingest", "--cpv", "72220000-3", "--limit", "5"])
    assert args.command == "ingest"
    assert args.cpv == "72220000-3"
    assert args.limit == 5


def test_cli_parse_command_arguments():
    parser = create_cli_parser()
    args = parser.parse_args(["parse", "--input-dir", "data_raw", "--output-dir", "data_processed"])
    assert args.command == "parse"
    assert args.input_dir == "data_raw"
    assert args.output_dir == "data_processed"


def test_cli_index_command_arguments():
    parser = create_cli_parser()
    args = parser.parse_args(["index", "--procurement-id", "PROC-123"])
    assert args.command == "index"
    assert args.procurement_id == "PROC-123"


def test_cli_requires_command():
    parser = create_cli_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_main_help_exits():
    from src.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_main_missing_required_analyze_argument():
    from src.cli import main
    with pytest.raises(SystemExit):
        main(["analyze"])


def test_main_parse_empty_dir(tmp_path):
    from src.cli import main
    input_dir = tmp_path / "empty_input"
    output_dir = tmp_path / "empty_output"
    input_dir.mkdir()
    output_dir.mkdir()
    exit_code = main(["parse", "--input-dir", str(input_dir), "--output-dir", str(output_dir)])
    assert exit_code == 0

