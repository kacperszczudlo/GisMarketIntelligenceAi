from unittest.mock import AsyncMock, patch
import pytest
from src.inference.models import TenderReport
from src.inference.report_generator import TenderReportGenerator


@pytest.mark.asyncio
async def test_report_generator_parses_sections():
    generator = TenderReportGenerator()

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

    with patch.object(generator.ollama, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = fake_llm_response

        report = await generator.generate(
            procurement_id="OCDS-TEST-123",
            title="Modernizacja BDOT500",
            municipality="Gmina Niepołomice",
            context="[Rozdział II] Wymóg formatu .str",
        )

        assert isinstance(report, TenderReport)
        assert report.procurement_id == "OCDS-TEST-123"
        assert report.municipality == "Gmina Niepołomice"
        assert "Niepołomice" in report.executive_summary
        assert ".str" in report.markdown_report
        assert len(report.citations) >= 1
