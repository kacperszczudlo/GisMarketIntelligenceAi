from typing import List
from unittest.mock import AsyncMock, patch
import pytest
from src.evaluation.ragas_guard import EvaluationResult, RagasGuard


def test_quality_gate_rejects_hallucinations():
    guard = RagasGuard(min_faithfulness=0.95)
    passed = guard.verify_metrics({"faithfulness": 0.88, "answer_relevancy": 0.92})
    assert passed is False


def test_quality_gate_accepts_grounded_report():
    guard = RagasGuard(min_faithfulness=0.95)
    passed = guard.verify_metrics({"faithfulness": 0.98, "answer_relevancy": 0.95})
    assert passed is True


def test_quality_gate_requires_faithfulness_above_threshold():
    guard = RagasGuard(min_faithfulness=0.95, min_answer_relevancy=0.80)
    # Exactly at threshold
    assert guard.verify_metrics({"faithfulness": 0.95, "answer_relevancy": 0.85}) is True
    # Below threshold
    assert guard.verify_metrics({"faithfulness": 0.949, "answer_relevancy": 0.85}) is False
    # Below answer relevancy
    assert guard.verify_metrics({"faithfulness": 0.96, "answer_relevancy": 0.79}) is False


def test_ragas_guard_heuristic_faithfulness_evaluation():
    guard = RagasGuard(min_faithfulness=0.95)

    contexts = [
        "Wymóg formatu .str dla bazy EWMAPA [Załącznik 2, strona 14].",
        "Zamawiający wymaga doświadczenia w modernizacji EGiB.",
    ]

    # Report grounded strictly in contexts
    grounded_answer = (
        "Postępowanie zawiera wymóg formatu .str dla bazy EWMAPA. "
        "Zamawiający wymaga również doświadczenia w modernizacji EGiB."
    )
    result = guard.evaluate_claims_grounding(grounded_answer, contexts)
    assert isinstance(result, EvaluationResult)
    assert result.faithfulness >= 0.95
    assert result.passed is True

    # Report with hallucinated claims
    hallucinated_answer = (
        "Wymóg formatu .str dla bazy EWMAPA. "
        "Zamawiający żąda wpłacenia wadium w wysokości 10 milionów złotych na konto w Szwajcarii. "
        "Wykonawca musi posiadać własnego satelitę szpiegowskiego na orbicie geostacjonarnej. "
        "Wymagane jest zatrudnienie 500 programistów w języku Fortran."
    )
    hallucinated_result = guard.evaluate_claims_grounding(hallucinated_answer, contexts)
    assert hallucinated_result.faithfulness < 0.95
    assert hallucinated_result.passed is False
    assert "Wskaźnik wierności faktom poniżej wymaganego progu" in (hallucinated_result.reason or "")


@pytest.mark.asyncio
async def test_ragas_guard_llm_judge():
    guard = RagasGuard(min_faithfulness=0.95)

    with patch.object(guard.ollama, "generate", new_callable=AsyncMock) as mock_gen:
        # Mock passing LLM judge response
        mock_gen.return_value = "FAITHFULNESS: 0.98\nRELEVANCY: 0.95"
        result = await guard.evaluate_with_llm_judge(
            question="Czy wymagany jest format .str?",
            answer="Tak, wymagany jest format .str dla bazy EWMAPA.",
            contexts=["Wymóg formatu .str dla bazy EWMAPA."],
        )
        assert result.faithfulness == 0.98
        assert result.answer_relevancy == 0.95
        assert result.passed is True

        # Mock failing LLM judge response (hallucination detected)
        mock_gen.return_value = "FAITHFULNESS: 0.60\nRELEVANCY: 0.90"
        failing_result = await guard.evaluate_with_llm_judge(
            question="Jakie jest wadium?",
            answer="Wadium wynosi 5 milionów zł.",
            contexts=["Brak informacji o wadium."],
        )
        assert failing_result.faithfulness == 0.60
        assert failing_result.passed is False
        assert "Wskaźnik wierności faktom poniżej wymaganego progu" in (failing_result.reason or "")

