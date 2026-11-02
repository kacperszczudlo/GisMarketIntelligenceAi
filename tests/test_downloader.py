import hashlib
from pathlib import Path
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from src.database.connection import db_manager
from src.ingestion.downloader import AttachmentDownloader


@pytest.mark.asyncio
async def test_downloader_streams_and_computes_sha256(tmp_path: Path):
    downloader = AttachmentDownloader(download_dir=tmp_path)
    sample_content = b"%PDF-1.5 Sample tender document with SWZ requirements."
    expected_hash = hashlib.sha256(sample_content).hexdigest()

    async def mock_streaming_response(*args, **kwargs):
        yield sample_content

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = lambda: None
    mock_response.aiter_bytes = mock_streaming_response

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_response
    mock_ctx.__aexit__.return_value = None

    with patch("httpx.AsyncClient.stream", return_value=mock_ctx):
        output_path, sha256_hash = await downloader.download_file(
            url="https://ezamowienia.gov.pl/files/swz.pdf",
            file_name="test_swz.pdf",
        )

        assert output_path.exists()
        assert output_path.read_bytes() == sample_content
        assert sha256_hash == expected_hash


def test_save_attachment_to_database():
    downloader = AttachmentDownloader()
    proc_id = uuid.uuid4()
    ocds_id = f"ocds-down-{str(proc_id)[:8]}"

    # Setup parent procurement in DB
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO procurements (id, ocds_id, title, municipality_name, voivodeship, date_published, date_deadline)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '7 days');
            """,
            (str(proc_id), ocds_id, "Tender for downloader test", "Gmina Test", "Lubelskie"),
        )

    # Save attachment via downloader
    test_hash = "f" * 64
    att_id = downloader.save_attachment_to_db(
        procurement_id=proc_id,
        file_name="OPZ_geodezja.pdf",
        file_type="OPZ",
        sha256_hash=test_hash,
        raw_markdown="# OPZ Treść",
    )

    assert att_id is not None

    # Verify presence in database
    with db_manager.get_cursor() as cur:
        cur.execute("SELECT file_name, file_type, sha256_hash FROM attachments WHERE id = %s;", (str(att_id),))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "OPZ_geodezja.pdf"
        assert row[1] == "OPZ"
        assert row[2] == test_hash

    # Cleanup
    with db_manager.get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM procurements WHERE id = %s;", (str(proc_id),))
