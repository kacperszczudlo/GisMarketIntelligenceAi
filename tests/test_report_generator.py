import pytest
from pytest_mock import MockerFixture
from src.inference.models import CompetitorItem, RedFlagItem, TenderReport
from src.inference.ollama_client import OllamaClient
from src.inference.report_generator import TenderReportGenerator

HTTP_STATUS_OK = 200
HTTP_STATUS_NOT_FOUND = 404


@pytest.mark.asyncio
async def test_should_generate_structured_report_and_extract_citations(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_ollama = mocker.MagicMock(spec=OllamaClient)
    fake_llm_response = (
        "### 1. Podsumowanie postępowania\n"
        "Postępowanie dotyczy modernizacji BDOT500 w gminie Niepołomice.\n\n"
        "### 2. Zidentyfikowane zastrzeżenia formalno-prawne\n"
        "Wymóg zamkniętego formatu .str dla bazy EWMAPA [Załącznik 2, strona 14].\n\n"
        "### 3. Zestawienie rozwiązań konkurencyjnych\n"
        "Geo-System posiada silną pozycję w regionie.\n\n"
        "### 4. Źródła danych\n"
        "- SWZ_Zalacznik_2.pdf, strona 14\n\n"
        "### 5. Rekomendacje dla zarządu\n"
        "Złożyć wniosek o zmianę SWZ na podstawie art. 16 PZP."
    )
    mock_ollama.generate = mocker.AsyncMock(return_value=fake_llm_response)
    generator = TenderReportGenerator(ollama_client=mock_ollama)

    # Act
    report = await generator.generate(
        procurement_id="OCDS-TEST-123",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        context="[Rozdział II] Wymóg formatu .str",
    )

    # Assert
    assert isinstance(report, TenderReport)
    assert report.procurement_id == "OCDS-TEST-123"
    assert report.municipality == "Gmina Niepołomice"
    assert "Niepołomice" in report.executive_summary
    assert ".str" in report.markdown_report
    assert "SWZ_Zalacznik_2.pdf, strona 14" in report.citations


@pytest.mark.asyncio
async def test_should_fallback_to_deterministic_synthesis_when_ollama_raises_exception(
    sample_swz_markdown: str,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_ollama = mocker.MagicMock(spec=OllamaClient)
    mock_ollama.generate = mocker.AsyncMock(side_effect=ConnectionError("Ollama offline"))
    generator = TenderReportGenerator(ollama_client=mock_ollama)

    # Act
    report = await generator.generate(
        procurement_id="OCDS-FALLBACK-1",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        context=sample_swz_markdown,
    )

    # Assert
    assert report.procurement_id == "OCDS-FALLBACK-1"
    assert "### 1. Podsumowanie postępowania" in report.raw_llm_output
    assert "BDOT500" in report.markdown_report
    assert ".str" in report.markdown_report


@pytest.mark.asyncio
async def test_should_skip_ollama_network_call_when_fast_synthesis_is_enabled(
    sample_swz_markdown: str,
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_ollama = mocker.MagicMock(spec=OllamaClient)
    mock_ollama.generate = mocker.AsyncMock()
    generator = TenderReportGenerator(ollama_client=mock_ollama)

    # Act
    report = await generator.generate(
        procurement_id="OCDS-FAST-1",
        title="Modernizacja BDOT500",
        municipality="Gmina Niepołomice",
        context=sample_swz_markdown,
        use_fast_synthesis=True,
    )

    # Assert
    mock_ollama.generate.assert_not_awaited()
    assert "### 2. Zidentyfikowane zastrzeżenia formalno-prawne" in report.markdown_report


@pytest.mark.parametrize(
    ("question", "expected_snippet"),
    [
        ("Ile wynosi wymagane wadium?", "9 000,00 PLN"),
        ("Jaką karę umowną za zwłokę przewidziano?", "2%"),
        ("Czy wymagany jest format .str w EWMAPA?", ".str"),
        ("Jakich uprawnień wymaga się od kierownika prac?", "zakresu 1 i 2"),
        ("Jaki jest budżet i wartość zamówienia BDOT500?", "320 000,00 PLN"),
        ("Jakie nietypowe słowa obrębów ewidencyjnych występują?", "obrębów"),
    ],
    ids=["wadium", "penalties", "format_lockin", "personnel", "budget_scope", "fallback_stem_scoring"],
)
def test_should_answer_specific_domain_questions_from_swz_context(
    sample_swz_markdown: str,
    question: str,
    expected_snippet: str,
) -> None:
    # Arrange & Act
    answer = TenderReportGenerator.answer_specific_question(question, sample_swz_markdown)

    # Assert
    assert expected_snippet in answer


def test_should_return_refusal_message_when_context_is_empty() -> None:
    # Arrange & Act
    answer = TenderReportGenerator.answer_specific_question("Jakie jest wadium?", "")
    empty_synthesis = TenderReportGenerator._build_grounded_synthesis("", "Gmina Test")

    # Assert
    assert answer == "Brak informacji w dostarczonej dokumentacji przetargowej."
    assert "Brak informacji w dostarczonej dokumentacji przetargowej." in empty_synthesis


@pytest.mark.asyncio
async def test_should_resolve_fallback_ollama_model_when_configured_model_returns_404(
    mocker: MockerFixture,
) -> None:
    # Arrange
    client = OllamaClient(base_url="http://localhost:11434", model="missing-model")

    resp_404 = mocker.MagicMock()
    resp_404.status_code = HTTP_STATUS_NOT_FOUND

    resp_tags = mocker.MagicMock()
    resp_tags.status_code = HTTP_STATUS_OK
    resp_tags.json.return_value = {"models": [{"name": "bielik:latest"}]}

    resp_200 = mocker.MagicMock()
    resp_200.status_code = HTTP_STATUS_OK
    resp_200.raise_for_status = mocker.MagicMock()
    resp_200.json.return_value = {"response": "Wygenerowana odpowiedź z modelu fallback."}

    mock_http = mocker.MagicMock()
    mock_http.post = mocker.AsyncMock(side_effect=[resp_404, resp_200])
    mock_http.get = mocker.AsyncMock(return_value=resp_tags)

    mock_ctx = mocker.MagicMock()
    mock_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = mocker.AsyncMock(return_value=None)
    mocker.patch("src.inference.ollama_client.httpx.AsyncClient", return_value=mock_ctx)

    # Act
    output = await client.generate(prompt="Test prompt", system="System prompt")

    # Assert
    assert output == "Wygenerowana odpowiedź z modelu fallback."
    assert client.model == "bielik:latest"
    assert mock_http.post.await_count == 2


@pytest.mark.asyncio
async def test_should_check_ollama_health_and_execute_chat_completion(
    mocker: MockerFixture,
) -> None:
    # Arrange
    client = OllamaClient(base_url="http://localhost:11434", model="gis-analyst")

    resp_tags = mocker.MagicMock()
    resp_tags.status_code = HTTP_STATUS_OK

    resp_chat = mocker.MagicMock()
    resp_chat.status_code = HTTP_STATUS_OK
    resp_chat.raise_for_status = mocker.MagicMock()
    resp_chat.json.return_value = {"message": {"content": "Odpowiedź czatu"}}

    mock_http = mocker.MagicMock()
    mock_http.get = mocker.AsyncMock(return_value=resp_tags)
    mock_http.post = mocker.AsyncMock(return_value=resp_chat)

    mock_ctx = mocker.MagicMock()
    mock_ctx.__aenter__ = mocker.AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = mocker.AsyncMock(return_value=None)
    mocker.patch("src.inference.ollama_client.httpx.AsyncClient", return_value=mock_ctx)

    # Act
    healthy = await client.check_health()
    chat_reply = await client.chat(messages=[{"role": "user", "content": "Pytanie"}])

    # Assert
    assert healthy is True
    assert chat_reply == "Odpowiedź czatu"


def test_should_instantiate_red_flag_and_competitor_models() -> None:
    # Arrange & Act
    flag = RedFlagItem(
        title="Wymóg formatu .str",
        location="OPZ Rozdział II",
        citation="Wymagany format .str",
        legal_basis="Art. 99 ust. 4 PZP",
        recommended_action="Odwołanie do KIO",
    )
    comp = CompetitorItem(
        name="Geo-System Sp. z o.o.",
        probability="Wysokie",
        strengths="Portal iMPA",
        weaknesses="Koszt wdrożenia",
    )

    # Assert
    assert flag.severity == "WYSOKIE"
    assert comp.name == "Geo-System Sp. z o.o."


def test_should_return_no_info_message_for_unrelated_question(sample_swz_markdown: str) -> None:
    answer = TenderReportGenerator.answer_specific_question(
        "Jaka jest dzisiaj pogoda w Warszawie i kurs euro?",
        sample_swz_markdown,
    )
    assert answer == "Brak informacji w dostarczonej dokumentacji przetargowej."


def test_should_export_markdown_report_to_valid_multipage_pdf_bytes() -> None:
    from src.inference.pdf_exporter import export_report_to_pdf_bytes

    long_md = "# Raport przetargowy: ocds-148610-niepolomice\n\n" + "\n".join(
        f"{idx}. Wymóg formalny nr {idx}: Zamawiający żąda formatu .str oraz kary 2%."
        for idx in range(1, 70)
    )
    pdf_bytes = export_report_to_pdf_bytes(long_md)

    assert pdf_bytes.startswith(b"%PDF-1.4\n")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert b"/Count 2" in pdf_bytes
    assert b"Strona 1/2" in pdf_bytes
    assert b"Strona 2/2" in pdf_bytes
