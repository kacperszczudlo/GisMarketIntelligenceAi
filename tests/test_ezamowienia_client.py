from unittest.mock import AsyncMock, patch
import pytest
from src.ingestion.client import EZamowieniaClient
from src.ingestion.models import TenderNotice


@pytest.mark.asyncio
async def test_ezamowienia_client_fetch_notices_mocked():
    client = EZamowieniaClient()
    mock_response_data = [
        {
            "ocds_id": "ocds-148610-99999",
            "title": "Budowa geoportalu gminnego i bazy BDOT500",
            "municipality_name": "Gmina Kórnik",
            "voivodeship": "Wielkopolskie",
            "estimated_budget_pln": 250000.0,
            "cpv_codes": ["72220000-3"],
            "date_published": "2026-04-10T08:00:00Z",
            "date_deadline": "2026-05-15T10:00:00Z",
            "status": "ACTIVE",
        }
    ]

    with patch.object(client, "_request_api", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response_data
        notices = await client.fetch_notices(cpv_codes=["72220000-3"], limit=1)

        assert len(notices) == 1
        assert isinstance(notices[0], TenderNotice)
        assert notices[0].ocds_id == "ocds-148610-99999"
        assert notices[0].municipality_name == "Gmina Kórnik"
        mock_req.assert_awaited_once()
        endpoint_called = mock_req.call_args[0][0]
        assert endpoint_called == "notice"


@pytest.mark.asyncio
async def test_ezamowienia_client_parses_bzp_feed():
    client = EZamowieniaClient()
    raw_notice = {
        "objectId": "ocds-148610-bzp-1",
        "orderObject": "Modernizacja ewidencji gruntów i budynków EGiB",
        "purchaserName": "Powiat Warszawski Zachodni",
        "purchaserProvince": "Mazowieckie",
        "tenderValue": 450000.0,
        "cpvCode": "71354300-7",
        "publicationDate": "2026-03-01T10:00:00Z",
        "submittingOffersDate": "2026-03-25T12:00:00Z",
    }
    normalized = client.normalize_notice(raw_notice)
    assert normalized.ocds_id == "ocds-148610-bzp-1"
    assert "71354300-7" in normalized.cpv_codes
    assert normalized.voivodeship == "Mazowieckie"


def test_ezamowienia_client_normalizes_live_bzp_format():
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
        "htmlBody": "<html><body><h1>Ogłoszenie SWZ</h1><p>Wymagany eksport do formatu .str programu EWMAPA.</p></body></html>",
    }
    normalized = client.normalize_notice(live_sample)
    assert normalized.ocds_id == "ocds-148610-77b4a0d6-0f31-4cce-871f-af8d5995d733"
    assert normalized.voivodeship == "Małopolskie"
    assert normalized.cpv_codes == ["71250000-5", "71354300-7"]
    assert len(normalized.attachments) == 1
    assert "EWMAPA" in (normalized.attachments[0].raw_markdown or "")
