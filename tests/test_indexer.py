from pathlib import Path
from typing import Any
import uuid
import pytest
from pytest_mock import MockerFixture
from src.indexing.embedder import EXPECTED_EMBEDDING_DIM, BgeM3Embedder
from src.indexing.indexer import DatabaseIndexer
from src.indexing.splitter import ParentChildSplitter

TEST_CHILD_CHUNK_SIZE = 50
TEST_CHILD_OVERLAP = 5
EXPECTED_MIN_CHUNKS = 2


def test_should_batch_insert_parents_and_1024_dim_children_in_transaction(
    mocker: MockerFixture,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_embedder = mocker.MagicMock(spec=BgeM3Embedder)
    fake_vec = [1.0] + [0.0] * (EXPECTED_EMBEDDING_DIM - 1)
    mock_embedder.embed_texts.side_effect = lambda texts, **kwargs: [fake_vec for _ in texts]

    splitter = ParentChildSplitter(child_size=TEST_CHILD_CHUNK_SIZE, child_overlap=TEST_CHILD_OVERLAP)
    indexer = DatabaseIndexer(embedder=mock_embedder, splitter=splitter)

    mock_execute_values = mocker.patch("src.indexing.indexer.psycopg2.extras.execute_values")
    att_id = uuid.uuid4()
    sample_md = (
        "# Rozdział I: Wymagania ogólne\n\n"
        "Modernizacja bazy danych BDOT500 oraz GESUT dla miasta Krakowa.\n\n"
        "## Rozdział II: Kluczowe terminy\n\n"
        "Termin realizacji wynosi 12 miesięcy od podpisania umowy.\n"
    )

    # Act
    indexed_count = indexer.index_document(sample_md, attachment_id=att_id)

    # Assert
    assert indexed_count >= EXPECTED_MIN_CHUNKS
    mock_embedder.embed_texts.assert_called_once()
    assert mock_execute_values.call_count == 2

    parent_call_args = mock_execute_values.call_args_list[0][0]
    assert parent_call_args[0] is mock_db_cursor
    assert "INSERT INTO parent_nodes" in parent_call_args[1]
    assert len(parent_call_args[2]) == 2

    child_call_args = mock_execute_values.call_args_list[1][0]
    assert "INSERT INTO chunk_vectors" in child_call_args[1]
    assert len(child_call_args[2]) == indexed_count


def test_should_return_zero_and_skip_database_when_markdown_is_empty(
    mocker: MockerFixture,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    mock_embedder = mocker.MagicMock(spec=BgeM3Embedder)
    indexer = DatabaseIndexer(embedder=mock_embedder)
    mock_execute_values = mocker.patch("src.indexing.indexer.psycopg2.extras.execute_values")

    # Act
    count = indexer.index_document("   \n  ", attachment_id=uuid.uuid4())

    # Assert
    assert count == 0
    mock_embedder.embed_texts.assert_not_called()
    mock_execute_values.assert_not_called()


def test_should_read_markdown_file_from_disk_and_index_contents(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    md_file = tmp_path / "SWZ_Krakow.md"
    md_file.write_text("# Rozdział I\nOpis zamówienia BDOT500.", encoding="utf-8")
    att_id = uuid.uuid4()

    indexer = DatabaseIndexer()
    mock_index_doc = mocker.patch.object(indexer, "index_document", return_value=3)

    # Act
    count = indexer.index_file(md_file, attachment_id=att_id)

    # Assert
    assert count == 3
    mock_index_doc.assert_called_once_with("# Rozdział I\nOpis zamówienia BDOT500.", attachment_id=att_id)


def test_should_raise_file_not_found_error_when_markdown_file_is_missing(
    tmp_path: Path,
) -> None:
    # Arrange
    indexer = DatabaseIndexer()
    missing_path = tmp_path / "missing.md"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Markdown file does not exist"):
        indexer.index_file(missing_path, attachment_id=uuid.uuid4())
