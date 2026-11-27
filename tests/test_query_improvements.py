"""Tests for query expansion, sparse stopword filtering, conversational prompts, and API LLM wiring."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.app import _OLLAMA_HEALTH_CACHE, _SUMMARY_CACHE, app
from src.auth.service import UserRecord, create_session_token
from src.inference.prompts import CONVERSATIONAL_SWZ_SYSTEM_PROMPT, build_chat_prompt
from src.retrieval.query_expander import expand_swz_query
from src.retrieval.sparse_search import SparseRetriever


def test_expand_swz_query_maps_vague_risk_question() -> None:
    expanded = expand_swz_query("czy są tu jakieś haczyki?")
    assert "vendor lock-in" in expanded
    assert "kary umowne" in expanded


def test_expand_swz_query_adds_anchors_for_short_unmatched_query() -> None:
    expanded = expand_swz_query("co wiesz o gminie")
    assert "przedmiot zamówienia" in expanded


def test_sparse_retriever_filters_polish_stopwords() -> None:
    tsquery = SparseRetriever._prepare_tsquery_terms("Czy jakie są kary umowne dla wykonawcy?")
    assert "Czy" not in tsquery
    assert "jakie" not in tsquery
    assert "dla" not in tsquery
    assert "kary" in tsquery
    assert "umowne" in tsquery


def test_build_chat_prompt_includes_history_and_format() -> None:
    prompt = build_chat_prompt(
        question="A jaki jest termin?",
        context="Termin realizacji: 12 miesięcy.",
        response_format="Zwięzły (Punkty)",
        history=[{"role": "user", "content": "O czym jest przetarg?"}],
    )
    assert "Użytkownik: O czym jest przetarg?" in prompt
    assert "krótkich, czytelnych punktach" in prompt
    assert "Termin realizacji: 12 miesięcy." in prompt
    assert "Brak informacji" not in CONVERSATIONAL_SWZ_SYSTEM_PROMPT[:100]


def test_api_ask_uses_ollama_when_healthy_and_reports_fallback_on_failure() -> None:
    _SUMMARY_CACHE.clear()
    _OLLAMA_HEALTH_CACHE["ts"] = 0.0
    admin = UserRecord(id=1, username="inspe", role="admin", is_active=True)
    token = create_session_token(admin)
    headers = {"Authorization": f"Bearer {token}"}

    sample_row = {
        "id": "ocds-148610-test-q",
        "title": "Wdrożenie GIS",
        "municipality": "Gmina Test",
        "voivodeship": "Wielkopolskie",
        "budget_pln": 500000.0,
        "published": "2026-10-01",
        "deadline": "2026-11-01",
        "status": "ACTIVE",
    }
    fake_pipeline = MagicMock()
    fake_pipeline.retrieve.return_value = [
        {"section_title": "OPZ", "cross_encoder_score": 0.92, "content": "Wymagany format GML."}
    ]
    fake_report = SimpleNamespace(markdown_report="# Raport", raw_llm_output="## Podsumowanie\nOK")
    fake_eval = SimpleNamespace(faithfulness=0.98)

    with patch("src.api.app.AuthService.ensure_schema_and_admin"), \
         patch("src.api.app._fetch_procurements_rows", return_value=[sample_row]), \
         patch("src.api.app._fetch_full_tender_context", return_value="Wymagany format GML."), \
         patch("src.api.app._get_pipeline", return_value=fake_pipeline), \
         patch("src.api.app.RagasGuard.evaluate_claims_grounding", return_value=fake_eval), \
         patch("src.api.app.TenderReportGenerator.generate", new=AsyncMock(return_value=fake_report)), \
         patch("src.api.app.OllamaClient.check_health", new=AsyncMock(return_value=True)), \
         patch("src.api.app.OllamaClient.generate", new=AsyncMock(return_value="Przetarg wymaga otwartego formatu GML.")):

        client = TestClient(app)
        resp = client.post(
            "/api/procurements/ocds-148610-test-q/ask",
            headers=headers,
            json={"question": "czy są tu jakieś haczyki?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine"] == "ollama"
        assert "GML" in data["answer"]

        # Verify stream emits fallback meta + notice when Ollama is offline
        with patch("src.api.app.OllamaClient.check_health", new=AsyncMock(return_value=False)):
            stream_resp = client.post(
                "/api/procurements/ocds-148610-test-q/ask/stream",
                headers=headers,
                json={"question": "czy są jakieś haczyki?"},
            )
            assert stream_resp.status_code == 200
            assert '"engine": "fallback"' in stream_resp.text
            assert "Tryb awaryjny" in stream_resp.text
