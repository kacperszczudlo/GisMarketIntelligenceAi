import pytest
import httpx
from unittest.mock import AsyncMock, patch
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


@pytest.mark.asyncio
async def test_ezamowienia_client_parses_bzp_feed():
    client = EZamowieniaClient()
    # Test normalization of public feed format into TenderNotice
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
