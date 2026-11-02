from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from src.ingestion.models import TenderNotice, AttachmentMetadata, CPVClassification


def test_valid_tender_notice_model():
    notice = TenderNotice(
        ocds_id="ocds-148610-12345",
        title="Dostawa oprogramowania GIS dla Urzędu Miasta",
        municipality_name="Miasto Poznań",
        voivodeship="Wielkopolskie",
        estimated_budget_pln=150000.00,
        cpv_codes=["48321000-4", "72220000-3"],
        date_published=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        date_deadline=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
        status="ACTIVE",
    )
    assert notice.ocds_id == "ocds-148610-12345"
    assert "48321000-4" in notice.cpv_codes
    assert notice.is_deadline_past() is True  # relative to future/past or current year


def test_tender_notice_validation_fails_on_empty_fields():
    with pytest.raises(ValidationError):
        TenderNotice(
            ocds_id="",
            title="",
            municipality_name="",
            voivodeship="",
            date_published=datetime.now(timezone.utc),
            date_deadline=datetime.now(timezone.utc),
        )


def test_attachment_metadata_model():
    att = AttachmentMetadata(
        file_name="SWZ_Zalacznik_1.pdf",
        file_type="SWZ",
        url="https://ezamowienia.gov.pl/mo-board/api/v1/notice/attachment/123",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    assert att.file_name.endswith(".pdf")
    assert att.file_type == "SWZ"
