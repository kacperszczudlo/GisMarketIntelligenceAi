import asyncio
from datetime import datetime, timezone
import hashlib
import logging
import random
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from bs4 import BeautifulSoup
import httpx

from src.database.connection import db_manager
from src.ingestion.models import AttachmentMetadata, TenderNotice
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

logger = logging.getLogger(__name__)

NUTS_PROVINCE_MAP: Dict[str, str] = {
    # TERYT / BZP province codes (PL + 2-digit GUS TERYT)
    "PL02": "Dolnośląskie",
    "PL04": "Kujawsko-Pomorskie",
    "PL06": "Lubelskie",
    "PL08": "Lubuskie",
    "PL10": "Łódzkie",
    "PL12": "Małopolskie",
    "PL14": "Mazowieckie",
    "PL16": "Opolskie",
    "PL18": "Podkarpackie",
    "PL20": "Podlaskie",
    "PL22": "Pomorskie",
    "PL24": "Śląskie",
    "PL26": "Świętokrzyskie",
    "PL28": "Warmińsko-Mazurskie",
    "PL30": "Wielkopolskie",
    "PL32": "Zachodniopomorskie",
    # NUTS-2 fallback codes
    "PL21": "Małopolskie",
    "PL41": "Wielkopolskie",
    "PL42": "Zachodniopomorskie",
    "PL43": "Lubuskie",
    "PL51": "Dolnośląskie",
    "PL52": "Opolskie",
    "PL61": "Kujawsko-Pomorskie",
    "PL62": "Warmińsko-Mazurskie",
    "PL63": "Pomorskie",
    "PL71": "Łódzkie",
    "PL72": "Świętokrzyskie",
    "PL81": "Lubelskie",
    "PL82": "Podkarpackie",
    "PL84": "Podlaskie",
    "PL91": "Mazowieckie",
    "PL92": "Mazowieckie",
}


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

    @staticmethod
    def _extract_html_to_markdown(html_body: str, title: str, ocds_id: str) -> str:
        """Converts BZP notice HTML body into structured Markdown."""
        soup = BeautifulSoup(html_body, "html.parser")
        for tag in soup(["style", "script"]):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        body_text = "\n".join(lines)
        return f"# Ogłoszenie BZP: {title}\n**ID Postępowania:** {ocds_id}\n\n## Treść ogłoszenia\n\n{body_text}\n"

    def normalize_notice(self, raw: Dict[str, Any]) -> TenderNotice:
        """Normalizes API JSON dictionary into a strongly typed TenderNotice model."""
        ocds_id = (
            raw.get("ocds_id")
            or raw.get("tenderId")
            or raw.get("objectId")
            or raw.get("noticeNumber")
            or "UNKNOWN_OCDS"
        )
        title = raw.get("title") or raw.get("orderObject") or "Brak tytułu postępowania"
        municipality = (
            raw.get("municipality_name")
            or raw.get("purchaserName")
            or raw.get("organizationName")
            or "Nieokreślony Zamawiający"
        )
        raw_prov = str(
            raw.get("voivodeship")
            or raw.get("purchaserProvince")
            or raw.get("organizationProvince")
            or raw.get("province")
            or "Polska"
        ).strip()
        voivodeship = NUTS_PROVINCE_MAP.get(raw_prov.upper(), raw_prov)

        budget = raw.get("estimated_budget_pln") or raw.get("tenderValue")

        # Normalize CPV codes
        raw_cpv = raw.get("cpv_codes") or raw.get("cpvCode") or []
        if isinstance(raw_cpv, str):
            extracted_codes = re.findall(r"\b\d{8}-\d\b", raw_cpv)
            if extracted_codes:
                cpv_codes = list(dict.fromkeys(extracted_codes))
            else:
                cpv_codes = [c.strip() for c in raw_cpv.split(",") if c.strip()]
        elif isinstance(raw_cpv, list):
            cpv_codes = [str(c).strip() for c in raw_cpv if str(c).strip()]
        else:
            cpv_codes = []

        # Parse publication date
        pub_raw = raw.get("date_published") or raw.get("publicationDate") or datetime.now(timezone.utc).isoformat()
        if isinstance(pub_raw, str):
            # Truncate nanoseconds if >6 fractional digits for Python <3.11 compatibility or clean ISO parsing
            pub_clean = re.sub(r"\.(\d{6})\d+", r".\1", pub_raw.replace("Z", "+00:00"))
            date_published = datetime.fromisoformat(pub_clean)
        else:
            date_published = pub_raw

        # Parse deadline date
        dead_raw = raw.get("date_deadline") or raw.get("submittingOffersDate") or datetime.now(timezone.utc).isoformat()
        if isinstance(dead_raw, str):
            dead_clean = re.sub(r"\.(\d{6})\d+", r".\1", dead_raw.replace("Z", "+00:00"))
            date_deadline = datetime.fromisoformat(dead_clean)
        else:
            date_deadline = dead_raw

        attachments: List[AttachmentMetadata] = []
        html_body = raw.get("htmlBody")
        if html_body and isinstance(html_body, str) and len(html_body.strip()) > 20:
            md_text = self._extract_html_to_markdown(html_body, title=title, ocds_id=ocds_id)
            digest = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
            safe_id = re.sub(r"[^\w\-]", "_", ocds_id)[:60]
            attachments.append(
                AttachmentMetadata(
                    file_name=f"BZP_{safe_id}.md",
                    file_type="BZP_NOTICE",
                    sha256_hash=digest,
                    raw_markdown=md_text,
                )
            )

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
            attachments=attachments,
        )

    async def fetch_notices(
        self,
        cpv_codes: List[str],
        limit: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        notice_type: str = "ContractNotice",
    ) -> List[TenderNotice]:
        """Fetches notices filtered by geodetic/GIS CPV codes from official BZP API."""
        params: Dict[str, Any] = {
            "NoticeType": notice_type,
            "PublicationDateFrom": date_from or "2025-01-01T00:00:00",
            "PublicationDateTo": date_to or datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59"),
            "PageSize": limit,
        }
        if cpv_codes:
            params["CpvCode"] = ",".join(cpv_codes)

        raw_items = await self._request_api("notice", params=params)
        if isinstance(raw_items, dict) and "items" in raw_items:
            items = raw_items["items"]
        elif isinstance(raw_items, list):
            items = raw_items
        else:
            items = []

        return [self.normalize_notice(item) for item in items[:limit]]

    def save_notice_to_db(self, notice: TenderNotice) -> UUID:
        """Upserts a tender notice and its inline BZP attachments into PostgreSQL."""
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
                    estimated_budget_pln = COALESCE(EXCLUDED.estimated_budget_pln, procurements.estimated_budget_pln),
                    cpv_codes = EXCLUDED.cpv_codes,
                    date_deadline = EXCLUDED.date_deadline,
                    status = EXCLUDED.status
                RETURNING id;
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
            row = cur.fetchone()
            db_proc_id = UUID(str(row[0])) if row else notice.id

            for att in notice.attachments:
                if att.raw_markdown and att.sha256_hash:
                    cur.execute(
                        "SELECT id FROM attachments WHERE procurement_id = %s AND sha256_hash = %s;",
                        (str(db_proc_id), att.sha256_hash),
                    )
                    if not cur.fetchone():
                        cur.execute(
                            """
                            INSERT INTO attachments (id, procurement_id, file_name, file_type, sha256_hash, raw_markdown)
                            VALUES (%s, %s, %s, %s, %s, %s);
                            """,
                            (
                                str(att.id),
                                str(db_proc_id),
                                att.file_name,
                                att.file_type,
                                att.sha256_hash,
                                att.raw_markdown,
                            ),
                        )

        return db_proc_id
