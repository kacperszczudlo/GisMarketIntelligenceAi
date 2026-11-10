from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
import pytest
from pytest_mock import MockerFixture

from src.database.connection import db_manager
from src.ingestion.models import AttachmentMetadata, TenderNotice


@pytest.fixture
def sample_swz_markdown() -> str:
    """Provides a realistic Polish GIS procurement SWZ/OPZ Markdown document for testing."""
    return (
        "# Rozdział I: Przedmiot i zakres zamówienia\n\n"
        "1. Przedmiotem zamówienia jest kompleksowa modernizacja bazy danych BDOT500 "
        "oraz inicjalizacja bazy GESUT dla obrębów ewidencyjnych Gminy Niepołomice.\n"
        "2. Szacunkowa wartość zamówienia wynosi 320 000,00 PLN netto.\n\n"
        "## Rozdział II: Wymagania techniczne i formaty wymiany danych\n\n"
        "1. Wykonawca zobowiązany jest do przekazania zmodernizowanych zbiorów danych "
        "w zamkniętym formacie natywnym .str kompatybilnym z oprogramowaniem EWMAPA "
        "producenta Geobid Sp. z o.o. bez udostępnienia struktury pośredniej.\n"
        "2. Zamawiający wymaga bezpośredniego zapisu operatów w bazie systemu OŚRODEK "
        "oraz pełnej integracji z portalem mapowym iMPA firmy Geo-System Sp. z o.o.\n\n"
        "### Rozdział III: Warunki udziału, wadium i kary umowne\n\n"
        "1. Kierownik prac geodezyjnych musi posiadać uprawnienia zawodowe zakresu 1 i 2 "
        "oraz minimum 5 lat doświadczenia w modernizacji baz EGiB.\n"
        "2. Wykonawca zobowiązany jest wnieść wadium w wysokości 9 000,00 PLN przed upływem terminu składania ofert.\n"
        "3. Za każdy dzień zwłoki Zamawiający naliczy karę umowną w wysokości 2% wynagrodzenia brutto "
        "bez górnego limitu kar."
    )


@pytest.fixture
def sample_tender_notice() -> TenderNotice:
    """Provides a valid TenderNotice domain model instance."""
    now = datetime.now(timezone.utc)
    return TenderNotice(
        ocds_id="ocds-148610-niepolomice",
        title="Modernizacja bazy BDOT500, GESUT oraz EGiB",
        municipality_name="Gmina Niepołomice",
        voivodeship="Małopolskie",
        estimated_budget_pln=320000.0,
        cpv_codes=["72220000-3", "71354300-7"],
        date_published=now - timedelta(days=3),
        date_deadline=now + timedelta(days=14),
        status="ACTIVE",
        attachments=[
            AttachmentMetadata(
                file_name="SWZ_Niepolomice.md",
                file_type="SWZ",
                sha256_hash="a" * 64,
                raw_markdown="# SWZ Gmina Niepołomice",
            )
        ],
    )


@pytest.fixture
def mock_db_cursor(mocker: MockerFixture) -> Any:
    """Mocks db_manager.get_cursor context manager and returns the underlying mock cursor."""
    cursor_mock = mocker.MagicMock(name="MockDatabaseCursor")

    @contextmanager
    def _fake_get_cursor(commit: bool = False) -> Generator[Any, None, None]:
        yield cursor_mock

    mocker.patch.object(db_manager, "get_cursor", side_effect=_fake_get_cursor)
    return cursor_mock
