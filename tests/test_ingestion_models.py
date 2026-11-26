from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from src.ingestion.models import AttachmentMetadata, CPVClassification, TenderNotice

SAMPLE_BUDGET_PLN = 150000.00
SHA256_EMPTY_STRING = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_should_create_valid_tender_notice_and_strip_surrounding_whitespace() -> None:
    # Arrange
    now = datetime.now(timezone.utc)

    # Act
    notice = TenderNotice(
        ocds_id="  ocds-148610-12345  ",
        title="  Dostawa oprogramowania GIS dla Urzędu Miasta  ",
        municipality_name="  Miasto Poznań  ",
        voivodeship="  Wielkopolskie  ",
        estimated_budget_pln=SAMPLE_BUDGET_PLN,
        cpv_codes=["48321000-4", "72220000-3"],
        date_published=now - timedelta(days=10),
        date_deadline=now - timedelta(days=1),
        status="ACTIVE",
    )

    # Assert
    assert notice.ocds_id == "ocds-148610-12345"
    assert notice.title == "Dostawa oprogramowania GIS dla Urzędu Miasta"
    assert notice.municipality_name == "Miasto Poznań"
    assert notice.voivodeship == "Wielkopolskie"
    assert "48321000-4" in notice.cpv_codes
    assert notice.is_deadline_past() is True


def test_should_evaluate_future_and_naive_deadlines_accurately() -> None:
    # Arrange
    now = datetime.now(timezone.utc)
    future_naive = (now + timedelta(days=5)).replace(tzinfo=None)

    notice = TenderNotice(
        ocds_id="ocds-148610-future",
        title="Modernizacja EGiB",
        municipality_name="Gmina Kórnik",
        voivodeship="Wielkopolskie",
        date_published=now,
        date_deadline=future_naive,
    )

    # Act
    is_past = notice.is_deadline_past()

    # Assert
    assert is_past is False


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("ocds_id", ""),
        ("ocds_id", "   "),
        ("title", ""),
        ("title", "\t\n "),
        ("municipality_name", "   "),
        ("voivodeship", ""),
    ],
    ids=[
        "empty_ocds_id",
        "whitespace_ocds_id",
        "empty_title",
        "whitespace_title",
        "whitespace_municipality",
        "empty_voivodeship",
    ],
)
def test_should_reject_tender_notice_when_required_text_field_is_blank(
    field_name: str,
    invalid_value: str,
) -> None:
    # Arrange
    now = datetime.now(timezone.utc)
    payload = {
        "ocds_id": "ocds-148610-valid",
        "title": "Poprawny tytuł zamówienia",
        "municipality_name": "Gmina Testowa",
        "voivodeship": "Mazowieckie",
        "date_published": now,
        "date_deadline": now,
        field_name: invalid_value,
    }

    # Act & Assert
    with pytest.raises(ValidationError):
        TenderNotice(**payload)


def test_should_validate_attachment_metadata_and_reject_blank_filename() -> None:
    # Arrange & Act
    att = AttachmentMetadata(
        file_name="  SWZ_Zalacznik_1.pdf  ",
        file_type="SWZ",
        url="https://ezamowienia.gov.pl/mo-board/api/v1/notice/attachment/123",
        sha256_hash=SHA256_EMPTY_STRING,
    )

    # Assert
    assert att.file_name == "SWZ_Zalacznik_1.pdf"
    assert att.file_type == "SWZ"

    with pytest.raises(ValidationError):
        AttachmentMetadata(file_name="   ")


def test_should_validate_cpv_classification_minimum_code_length() -> None:
    # Arrange & Act
    cpv = CPVClassification(code="72220000-3", name="Usługi doradcze w zakresie systemów")

    # Assert
    assert cpv.code == "72220000-3"

    with pytest.raises(ValidationError):
        CPVClassification(code="123")


def test_should_reject_negative_budget_and_deadline_before_published() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        TenderNotice(
            ocds_id="ocds-neg",
            title="Test",
            municipality_name="Gmina",
            voivodeship="Mazowieckie",
            estimated_budget_pln=-100.0,
            date_published=now,
            date_deadline=now + timedelta(days=1),
        )

    with pytest.raises(ValidationError):
        TenderNotice(
            ocds_id="ocds-bad-date",
            title="Test",
            municipality_name="Gmina",
            voivodeship="Mazowieckie",
            estimated_budget_pln=1000.0,
            date_published=now,
            date_deadline=now - timedelta(days=1),
        )
