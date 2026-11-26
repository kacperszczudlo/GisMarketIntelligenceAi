"""Unit tests for the FastAPI REST backend."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.app import _OLLAMA_HEALTH_CACHE, _PDF_CACHE, _SUMMARY_CACHE, app
from src.auth.service import UserRecord, create_session_token


def _make_user(username: str = "inspe", role: str = "admin", is_active: bool = True) -> UserRecord:
    return UserRecord(id=1, username=username, role=role, is_active=is_active)


def test_login_success_and_me():
    admin = _make_user("inspe", "admin", True)
    with patch("src.api.app.AuthService.authenticate", return_value=admin), \
         patch("src.api.app.AuthService.ensure_schema_and_admin"):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={"username": "inspe", "password": "secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["username"] == "inspe"
        assert data["user"]["role"] == "admin"
        token = data["token"]

        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "inspe"


def test_login_invalid_credentials():
    with patch("src.api.app.AuthService.authenticate", return_value=None), \
         patch("src.api.app.AuthService.ensure_schema_and_admin"):
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={"username": "inspe", "password": "wrong"})
        assert resp.status_code == 401


def test_users_crud_requires_admin():
    regular = _make_user("jan", "user", True)
    admin = _make_user("inspe", "admin", True)
    regular_token = create_session_token(regular)
    admin_token = create_session_token(admin)

    with patch("src.api.app.AuthService.ensure_schema_and_admin"):
        client = TestClient(app)

        forbidden = client.get("/api/users", headers={"Authorization": f"Bearer {regular_token}"})
        assert forbidden.status_code == 403

        with patch("src.api.app.AuthService.list_users", return_value=[admin, regular]):
            ok = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"})
            assert ok.status_code == 200
            assert len(ok.json()) == 1
            assert ok.json()[0]["username"] == "jan"

        created = _make_user("kacper", "user", True)
        with patch("src.api.app.AuthService.create_user", return_value=created):
            post_resp = client.post(
                "/api/users",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"username": "kacper", "password": "password123"},
            )
            assert post_resp.status_code == 201
            assert post_resp.json()["username"] == "kacper"

        with patch("src.api.app.AuthService.update_user_password", return_value=True):
            pw_resp = client.patch(
                "/api/users/kacper/password",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"new_password": "newpassword123"},
            )
            assert pw_resp.status_code == 200

        with patch("src.api.app.AuthService.set_user_active", return_value=True):
            act_resp = client.patch(
                "/api/users/kacper/active",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"is_active": False},
            )
            assert act_resp.status_code == 200
            assert act_resp.json()["is_active"] is False

        with patch("src.api.app.AuthService.delete_user", return_value=True):
            del_resp = client.delete(
                "/api/users/kacper",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert del_resp.status_code == 200


def test_procurements_summary_ask_pdf_and_about():
    _SUMMARY_CACHE.clear()
    _PDF_CACHE.clear()
    _OLLAMA_HEALTH_CACHE["ts"] = 0.0

    admin = _make_user("inspe", "admin", True)
    token = create_session_token(admin)
    sample_row = {
        "id": "ocds-148610-test",
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
        {"section_title": "Kary umowne", "rerank_score": 0.91, "content": "Kara 0,2% za dzień zwłoki."}
    ]

    fake_report = SimpleNamespace(
        markdown_report="# Raport\nTreść raportu",
        raw_llm_output="## Podsumowanie\nOK",
    )
    fake_eval = SimpleNamespace(faithfulness=0.97)

    with patch("src.api.app.AuthService.ensure_schema_and_admin"), \
         patch("src.api.app._fetch_procurements_rows", return_value=[sample_row]), \
         patch("src.api.app._fetch_full_tender_context", return_value="Wymagany otwartym standardzie GML i wadium 5 000,00 PLN."), \
         patch("src.api.app._get_pipeline", return_value=fake_pipeline), \
         patch("src.api.app.RagasGuard.evaluate_claims_grounding", return_value=fake_eval), \
         patch("src.api.app.TenderReportGenerator.generate", new=AsyncMock(return_value=fake_report)), \
         patch("src.api.app.TenderReportGenerator.answer_specific_question", return_value="Maksymalna kara wynosi 0,2% dziennie."), \
         patch("src.api.app.OllamaClient.check_health", new=AsyncMock(return_value=True)), \
         patch("src.api.app.OllamaClient.generate_json", new=AsyncMock(return_value={"penalty_rate": "0,2% / dzień"})), \
         patch("src.api.app.export_report_to_pdf_bytes", return_value=b"%PDF-1.4\n%fake"):

        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}

        list_resp = client.get("/api/procurements", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json()[0]["id"] == "ocds-148610-test"

        sum_resp = client.get("/api/procurements/ocds-148610-test/summary", headers=headers)
        assert sum_resp.status_code == 200
        assert sum_resp.json()["metrics"]["kio_level"] == "LOW"
        assert sum_resp.json()["faithfulness"] == 0.97

        ask_resp = client.post(
            "/api/procurements/ocds-148610-test/ask",
            headers=headers,
            json={"question": "Jakie są kary umowne?", "response_format": "Standard (SWZ)"},
        )
        assert ask_resp.status_code == 200
        assert "0,2%" in ask_resp.json()["answer"]
        assert len(ask_resp.json()["chunks"]) == 1

        pdf_resp = client.get(f"/api/procurements/ocds-148610-test/report.pdf?token={token}")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"].startswith("application/pdf")
        assert pdf_resp.content.startswith(b"%PDF")

        about_resp = client.get("/api/system/about", headers=headers)
        assert about_resp.status_code == 200
        assert about_resp.json()["ollama_ok"] is True
        assert about_resp.json()["total_tenders"] == 1

        async def _fake_stream(*_args, **_kwargs):
            yield "Kara "
            yield "0,2%"

        with patch("src.api.app.OllamaClient.stream_generate", side_effect=_fake_stream):
            stream_resp = client.post(
                "/api/procurements/ocds-148610-test/ask/stream",
                headers=headers,
                json={"question": "Jakie są kary?", "response_format": "Standard (SWZ)"},
            )
            assert stream_resp.status_code == 200
            body = stream_resp.text
            assert '"type": "chunks"' in body
            assert '"type": "token"' in body
            assert '"type": "done"' in body
