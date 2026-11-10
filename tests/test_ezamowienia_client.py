from typing import Any
import uuid
import httpx
import pytest
from pytest_mock import MockerFixture
from src.ingestion.client import EZamowieniaClient, NUTS_PROVINCE_MAP
from src.ingestion.models import TenderNotice
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

HTTP_STATUS_OK = 200
HTTP_STATUS_TOO_MANY_REQUESTS = 429
HTTP_STATUS_SERVICE_UNAVAILABLE = 503
SAMPLE_BUDGET_KORNIK = 250000.0
SAMPLE_BUDGET_WARSZAWA = 450000.0


@pytest.mark.asyncio
async def test_should_fetch_and_normalize_notices_from_ezamowienia_api(
    mocker: MockerFixture,
) -> None:
    # Arrange
    client = EZamowieniaClient()
    mock_response_data = [
        {
            "ocds_id": "ocds-148610-99999",
            "title": "Budowa geoportalu gminnego i bazy BDOT500",
            "municipality_name": "Gmina Kórnik",
            "voivodeship": "Wielkopolskie",
            "estimated_budget_pln": SAMPLE_BUDGET_KORNIK,
            "cpv_codes": ["72220000-3"],
            "date_published": "2026-04-10T08:00:00Z",
            "date_deadline": "2026-05-15T10:00:00Z",
            "status": "ACTIVE",
        }
    ]
    mock_req = mocker.patch.object(
        client,
        "_request_api",
        new_callable=mocker.AsyncMock,
        return_value=mock_response_data,
    )

    # Act
    notices = await client.fetch_notices(cpv_codes=["72220000-3"], limit=1)

    # Assert
    assert len(notices) == 1
    assert isinstance(notices[0], TenderNotice)
    assert notices[0].ocds_id == "ocds-148610-99999"
    assert notices[0].municipality_name == "Gmina Kórnik"
    mock_req.assert_awaited_once()
    assert mock_req.call_args[0][0] == "notice"


def test_should_normalize_bzp_dictionary_payload_into_tender_notice() -> None:
    # Arrange
    client = EZamowieniaClient()
    raw_notice = {
        "objectId": "ocds-148610-bzp-1",
        "orderObject": "Modernizacja ewidencji gruntów i budynków EGiB",
        "purchaserName": "Powiat Warszawski Zachodni",
        "purchaserProvince": "Mazowieckie",
        "tenderValue": SAMPLE_BUDGET_WARSZAWA,
        "cpvCode": "71354300-7",
        "publicationDate": "2026-03-01T10:00:00Z",
        "submittingOffersDate": "2026-03-25T12:00:00Z",
    }

    # Act
    normalized = client.normalize_notice(raw_notice)

    # Assert
    assert normalized.ocds_id == "ocds-148610-bzp-1"
    assert normalized.cpv_codes == ["71354300-7"]
    assert normalized.voivodeship == "Mazowieckie"
    assert normalized.estimated_budget_pln == SAMPLE_BUDGET_WARSZAWA


def test_should_normalize_live_bzp_format_with_html_body_and_nuts_province() -> None:
    # Arrange
    client = EZamowieniaClient()
    live_sample = {
        "tenderId": "ocds-148610-77b4a0d6-0f31-4cce-871f-af8d5995d733",
        "objectId": "08dd2b37-14f9-4a1c-aa0d-d80001d3bd86",
        "orderObject": "Modernizacja bazy BDOT500 i GESUT",
        "organizationName": "Gmina Niepołomice",
        "organizationProvince": "PL21",
        "cpvCode": "71250000-5 (Usługi architektoniczne),71354300-7 (Usługi badań katastralnych)",
        "publicationDate": "2025-01-02T14:09:33.1150927Z",
        "submittingOffersDate": "2025-01-13T09:00:00Z",
        "htmlBody": (
            "<html><head><style>body{color:red}</style></head>"
            "<body><h1>Ogłoszenie SWZ</h1><p>Wymagany eksport do formatu .str programu EWMAPA.</p></body></html>"
        ),
    }

    # Act
    normalized = client.normalize_notice(live_sample)

    # Assert
    assert normalized.ocds_id == "ocds-148610-77b4a0d6-0f31-4cce-871f-af8d5995d733"
    assert normalized.voivodeship == "Małopolskie"
    assert normalized.cpv_codes == ["71250000-5", "71354300-7"]
    assert len(normalized.attachments) == 1
    assert "EWMAPA" in (normalized.attachments[0].raw_markdown or "")
    assert "color:red" not in (normalized.attachments[0].raw_markdown or "")


@pytest.mark.parametrize(
    ("province_code", "expected_voivodeship"),
    [
        ("PL12", "Małopolskie"),
        ("PL21", "Małopolskie"),
        ("PL14", "Mazowieckie"),
        ("PL30", "Wielkopolskie"),
        ("PL02", "Dolnośląskie"),
    ],
    ids=["teryt_malopolskie", "nuts_malopolskie", "teryt_mazowieckie", "teryt_wielkopolskie", "teryt_dolnoslaskie"],
)
def test_should_map_teryt_and_nuts_codes_to_polish_voivodeship_names(
    province_code: str,
    expected_voivodeship: str,
) -> None:
    # Arrange & Act
    resolved = NUTS_PROVINCE_MAP[province_code]

    # Assert
    assert resolved == expected_voivodeship


@pytest.mark.asyncio
async def test_should_retry_api_request_when_rate_limited_with_429(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_limiter = mocker.MagicMock(spec=LeakyBucketRateLimiter)
    mock_limiter.acquire = mocker.AsyncMock()
    client = EZamowieniaClient(rate_limiter=mock_limiter)
    mocker.patch("src.ingestion.client.asyncio.sleep", new_callable=mocker.AsyncMock)

    resp_429 = mocker.MagicMock()
    resp_429.status_code = HTTP_STATUS_TOO_MANY_REQUESTS

    resp_200 = mocker.MagicMock()
    resp_200.status_code = HTTP_STATUS_OK
    resp_200.raise_for_status = mocker.MagicMock()
    resp_200.json.return_value = [{"ocds_id": "ocds-retry-ok"}]

    mock_http = mocker.MagicMock()
    mock_http.get = mocker.AsyncMock(side_effect=[resp_429, resp_200])
    mock_ctx = mocker.MagicMock()
    mock_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = mocker.AsyncMock(return_value=None)
    mocker.patch("src.ingestion.client.httpx.AsyncClient", return_value=mock_ctx)

    # Act
    data = await client._request_api("notice", max_retries=2)

    # Assert
    assert data == [{"ocds_id": "ocds-retry-ok"}]
    assert mock_http.get.await_count == 2


def test_should_upsert_notice_and_insert_new_attachment_into_database(
    sample_tender_notice: TenderNotice,
    mock_db_cursor: Any,
) -> None:
    # Arrange
    client = EZamowieniaClient()
    expected_proc_uuid = uuid.uuid4()
    mock_db_cursor.fetchone.side_effect = [(str(expected_proc_uuid),), None]

    # Act
    saved_id = client.save_notice_to_db(sample_tender_notice)

    # Assert
    assert saved_id == expected_proc_uuid
    assert mock_db_cursor.execute.call_count == 3
    first_sql = mock_db_cursor.execute.call_args_list[0][0][0]
    third_sql = mock_db_cursor.execute.call_args_list[2][0][0]
    assert "INSERT INTO procurements" in first_sql
    assert "ON CONFLICT (ocds_id) DO UPDATE" in first_sql
    assert "INSERT INTO attachments" in third_sql


@pytest.mark.asyncio
async def test_should_raise_request_error_after_exhausting_all_retries(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_limiter = mocker.MagicMock(spec=LeakyBucketRateLimiter)
    mock_limiter.acquire = mocker.AsyncMock()
    client = EZamowieniaClient(rate_limiter=mock_limiter)
    mocker.patch("src.ingestion.client.asyncio.sleep", new_callable=mocker.AsyncMock)

    req = httpx.Request("GET", "https://ezamowienia.gov.pl/mo-board/api/v1/notice")
    mock_http = mocker.MagicMock()
    mock_http.get = mocker.AsyncMock(side_effect=httpx.RequestError("Network down", request=req))
    mock_ctx = mocker.MagicMock()
    mock_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = mocker.AsyncMock(return_value=None)
    mocker.patch("src.ingestion.client.httpx.AsyncClient", return_value=mock_ctx)

    # Act & Assert
    with pytest.raises(httpx.RequestError, match="Network down"):
        await client._request_api("notice", max_retries=2)

    assert mock_http.get.await_count == 2

