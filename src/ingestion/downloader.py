import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID, uuid4
import httpx

from src.config import settings
from src.database.connection import db_manager
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

logger = logging.getLogger(__name__)


class AttachmentDownloader:
    """Asynchronous streaming downloader for procurement PDF/archive attachments with SHA-256 verification."""

    def __init__(
        self,
        download_dir: Optional[Path] = None,
        rate_limiter: Optional[LeakyBucketRateLimiter] = None,
        timeout: float = 60.0,
    ) -> None:
        self.download_dir = download_dir or settings.RAW_DATA_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.limiter = rate_limiter or LeakyBucketRateLimiter(max_requests=28, period_seconds=60.0)
        self.timeout = timeout

    async def download_file(self, url: str, file_name: str) -> Tuple[Path, str]:
        """Streams a file from URL to local disk while computing SHA-256 checksum on the fly."""
        await self.limiter.acquire()
        target_path = self.download_dir / file_name
        hasher = hashlib.sha256()

        headers = {
            "User-Agent": "GisMarketIntelligence/1.0 (Local Attachment Downloader)",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                with open(target_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if chunk:
                            hasher.update(chunk)
                            f.write(chunk)

        sha256_digest = hasher.hexdigest()
        logger.info("Successfully downloaded %s (SHA-256: %s)", target_path, sha256_digest)
        return target_path, sha256_digest

    def save_attachment_to_db(
        self,
        procurement_id: UUID,
        file_name: str,
        file_type: str,
        sha256_hash: str,
        raw_markdown: str = "",
    ) -> UUID:
        """Stores or updates attachment record in PostgreSQL attachments table."""
        attachment_id = uuid4()
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO attachments (
                    id, procurement_id, file_name, file_type, sha256_hash, raw_markdown
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    str(attachment_id),
                    str(procurement_id),
                    file_name,
                    file_type,
                    sha256_hash,
                    raw_markdown,
                ),
            )
            res = cur.fetchone()
            return UUID(res[0])
