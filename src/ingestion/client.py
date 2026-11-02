import asyncio
from datetime import datetime, timezone
import logging
import random
from typing import Any, Dict, List, Optional
import httpx

from src.database.connection import db_manager
from src.ingestion.models import TenderNotice
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

logger = logging.getLogger(__name__)


class EZamowieniaClient:
    """Asynchronous client for interacting with the Polish public procurement platform e-Zamowienia."""

    DEFAULT_BASE_URL = "https://ezamowienia.gov.pl/mo-board/api/v1"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        rate_limiter: Optional[LeakyBucketRateLimiter] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.limiter = rate_limiter or LeakyBucketRateLimiter(max_requests=28, period_seconds=60.0)
        self.timeout = timeout
        self.headers = {
            "User-Agent": "GisMarketIntelligence/1.0 (Local RAG Analysis)",
            "Accept": "application/json",
        }

    async def _request_api(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3
    ) -> Any:
        """Executes rate-limited HTTP GET request with exponential backoff and jitter."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        delay = 1.0

        for attempt in range(1, max_retries + 1):
            await self.limiter.acquire()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=self.headers)
                    if response.status_code in (429, 503):
                        logger.warning(
                            "e-Zamowienia API returned %s. Attempt %d/%d, retrying after %.2fs",
                            response.status_code,
                            attempt,
                            max_retries,
                            delay,
                        )
                        jitter = random.uniform(0.1, 0.5)
                        await asyncio.sleep(delay + jitter)
                        delay *= 2
                        continue

                    response.raise_for_status()
                    return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt == max_retries:
                    logger.error("Failed request to %s after %d attempts: %s", url, max_retries, exc)
                    raise
                jitter = random.uniform(0.1, 0.5)
                await asyncio.sleep(delay + jitter)
                delay *= 2

        raise RuntimeError(f"Failed to fetch data from {url}")

    def normalize_notice(self, raw: Dict[str, Any]) -> TenderNotice:
        """Normalizes API JSON dictionary into a strongly typed TenderNotice model."""
        ocds_id = raw.get("ocds_id") or raw.get("objectId") or raw.get("noticeNumber") or "UNKNOWN_OCDS"
        title = raw.get("title") or raw.get("orderObject") or "Brak tytułu postępowania"
        municipality = (
            raw.get("municipality_name")
            or raw.get("purchaserName")
            or raw.get("organizationName")
            or "Nieokreślony Zamawiający"
        )
        voivodeship = (
            raw.get("voivodeship")
            or raw.get("purchaserProvince")
            or raw.get("province")
            or "Polska"
        )
        budget = raw.get("estimated_budget_pln") or raw.get("tenderValue")

        # Normalize CPV codes
        raw_cpv = raw.get("cpv_codes") or raw.get("cpvCode") or []
        if isinstance(raw_cpv, str):
            cpv_codes = [c.strip() for c in raw_cpv.split(",") if c.strip()]
        elif isinstance(raw_cpv, list):
            cpv_codes = [str(c).strip() for c in raw_cpv if str(c).strip()]
        else:
            cpv_codes = []

        # Parse publication date
        pub_raw = raw.get("date_published") or raw.get("publicationDate") or datetime.now(timezone.utc).isoformat()
        if isinstance(pub_raw, str):
            date_published = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
        else:
            date_published = pub_raw

        # Parse deadline date
        dead_raw = raw.get("date_deadline") or raw.get("submittingOffersDate") or datetime.now(timezone.utc).isoformat()
        if isinstance(dead_raw, str):
            date_deadline = datetime.fromisoformat(dead_raw.replace("Z", "+00:00"))
        else:
            date_deadline = dead_raw

        return TenderNotice(
            ocds_id=ocds_id,
            title=title,
            municipality_name=municipality,
            voivodeship=voivodeship,
            estimated_budget_pln=float(budget) if budget is not None else None,
            cpv_codes=cpv_codes,
            date_published=date_published,
            date_deadline=date_deadline,
            status=raw.get("status", "ACTIVE"),
        )

    async def fetch_notices(
        self, cpv_codes: List[str], limit: int = 10, date_from: Optional[str] = None
    ) -> List[TenderNotice]:
        """Fetches notices filtered by geodetic/GIS CPV codes."""
        params: Dict[str, Any] = {"pageSize": limit}
        if cpv_codes:
            params["cpvCode"] = ",".join(cpv_codes)
        if date_from:
            params["dateFrom"] = date_from

        raw_items = await self._request_api("Notice/search", params=params)
        if isinstance(raw_items, dict) and "items" in raw_items:
            items = raw_items["items"]
        elif isinstance(raw_items, list):
            items = raw_items
        else:
            items = []

        return [self.normalize_notice(item) for item in items[:limit]]

    def save_notice_to_db(self, notice: TenderNotice) -> None:
        """Upserts a tender notice into the PostgreSQL procurements table."""
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO procurements (
                    id, ocds_id, title, municipality_name, voivodeship,
                    estimated_budget_pln, cpv_codes, date_published, date_deadline, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ocds_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    municipality_name = EXCLUDED.municipality_name,
                    voivodeship = EXCLUDED.voivodeship,
                    estimated_budget_pln = EXCLUDED.estimated_budget_pln,
                    cpv_codes = EXCLUDED.cpv_codes,
                    date_deadline = EXCLUDED.date_deadline,
                    status = EXCLUDED.status;
                """,
                (
                    str(notice.id),
                    notice.ocds_id,
                    notice.title,
                    notice.municipality_name,
                    notice.voivodeship,
                    notice.estimated_budget_pln,
                    notice.cpv_codes,
                    notice.date_published,
                    notice.date_deadline,
                    notice.status,
                ),
            )
