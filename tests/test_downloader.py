import hashlib
from pathlib import Path
from typing import Any, AsyncGenerator
import uuid
import httpx
import pytest
from pytest_mock import MockerFixture
from src.ingestion.downloader import AttachmentDownloader
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

HTTP_STATUS_OK = 200
HTTP_STATUS_NOT_FOUND = 404
SHA256_HEX_LENGTH = 64


@pytest.mark.asyncio
async def test_should_stream_file_chunks_and_compute_matching_sha256(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_limiter = mocker.MagicMock(spec=LeakyBucketRateLimiter)
    mock_limiter.acquire = mocker.AsyncMock()
    downloader = AttachmentDownloader(download_dir=tmp_path, rate_limiter=mock_limiter)

    chunk_1 = b"%PDF-1.5 Sample tender "
    chunk_2 = b"document with SWZ requirements."
    expected_content = chunk_1 + chunk_2
    expected_hash = hashlib.sha256(expected_content).hexdigest()

    async def _fake_aiter_bytes(chunk_size: int = 65536) -> AsyncGenerator[bytes, None]:
        yield chunk_1
        yield b""
        yield chunk_2

    mock_response = mocker.MagicMock()
    mock_response.status_code = HTTP_STATUS_OK
    mock_response.raise_for_status = mocker.MagicMock()
    mock_response.aiter_bytes = _fake_aiter_bytes

    mock_stream_ctx = mocker.MagicMock()
    mock_stream_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_http_client = mocker.MagicMock()
    mock_http_client.stream.return_value = mock_stream_ctx
    mock_client_ctx = mocker.MagicMock()
    mock_client_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http_client)
    mock_client_ctx.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("src.ingestion.downloader.httpx.AsyncClient", return_value=mock_client_ctx)

    # Act
    output_path, sha256_hash = await downloader.download_file(
        url="https://ezamowienia.gov.pl/files/swz.pdf",
        file_name="test_swz.pdf",
    )

    # Assert
    mock_limiter.acquire.assert_awaited_once()
    assert output_path.exists()
    assert output_path.read_bytes() == expected_content
    assert sha256_hash == expected_hash


@pytest.mark.asyncio
async def test_should_propagate_http_status_error_when_download_fails(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_limiter = mocker.MagicMock(spec=LeakyBucketRateLimiter)
    mock_limiter.acquire = mocker.AsyncMock()
    downloader = AttachmentDownloader(download_dir=tmp_path, rate_limiter=mock_limiter)

    request = httpx.Request("GET", "https://ezamowienia.gov.pl/files/missing.pdf")
    response = httpx.Response(HTTP_STATUS_NOT_FOUND, request=request)

    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=request,
        response=response,
    )

    mock_stream_ctx = mocker.MagicMock()
    mock_stream_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = mocker.AsyncMock(return_value=None)

    mock_http_client = mocker.MagicMock()
    mock_http_client.stream.return_value = mock_stream_ctx
    mock_client_ctx = mocker.MagicMock()
    mock_client_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http_client)
    mock_client_ctx.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("src.ingestion.downloader.httpx.AsyncClient", return_value=mock_client_ctx)

    # Act & Assert
    with pytest.raises(httpx.HTTPStatusError):
        await downloader.download_file(
            url="https://ezamowienia.gov.pl/files/missing.pdf",
            file_name="missing.pdf",
        )


def test_should_persist_attachment_record_to_database_and_return_uuid(
    tmp_path: Path,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    downloader = AttachmentDownloader(download_dir=tmp_path)
    proc_id = uuid.uuid4()
    expected_att_id = uuid.uuid4()
    mock_db_cursor.fetchone.return_value = (str(expected_att_id),)
    test_hash = "f" * SHA256_HEX_LENGTH

    # Act
    att_id = downloader.save_attachment_to_db(
        procurement_id=proc_id,
        file_name="OPZ_geodezja.pdf",
        file_type="OPZ",
        sha256_hash=test_hash,
        raw_markdown="# OPZ Treść",
    )

    # Assert
    assert att_id == expected_att_id
    mock_db_cursor.execute.assert_called_once()
    executed_sql, executed_params = mock_db_cursor.execute.call_args[0]
    assert "INSERT INTO attachments" in executed_sql
    assert executed_params[1] == str(proc_id)
    assert executed_params[2] == "OPZ_geodezja.pdf"
    assert executed_params[3] == "OPZ"
    assert executed_params[4] == test_hash
    assert executed_params[5] == "# OPZ Treść"
