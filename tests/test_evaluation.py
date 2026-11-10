from typing import Dict
import pytest
from pytest_mock import MockerFixture
from src.evaluation.ragas_guard import EvaluationResult, RagasGuard
from src.inference.ollama_client import OllamaClient

DEFAULT_MIN_FAITHFULNESS = 0.95
DEFAULT_MIN_RELEVANCY = 0.80
DEFAULT_MIN_PRECISION = 0.70


@pytest.mark.parametrize(
    ("metrics", "expected_passed"),
    [
        ({"faithfulness": 0.98, "answer_relevancy": 0.95}, True),
        ({"faithfulness": 0.95, "answer_relevancy": 0.80, "context_precision": 0.70}, True),
        ({"faithfulness": 0.88, "answer_relevancy": 0.92}, False),
        ({"faithfulness": 0.949, "answer_relevancy": 0.85}, False),
        ({"faithfulness": 0.96, "answer_relevancy": 0.79}, False),
        ({"faithfulness": 0.97, "answer_relevancy": 0.90, "context_precision": 0.65}, False),
        ({}, False),
    ],
    ids=[
        "high_scores_pass",
        "exact_boundary_thresholds_pass",
        "low_faithfulness_rejected",
        "just_below_faithfulness_rejected",
        "low_answer_relevancy_rejected",
        "low_context_precision_rejected",
        "empty_metrics_rejected",
    ],
)
def test_should_verify_metrics_against_configured_quality_gate_thresholds(
    metrics: Dict[str, float],
    expected_passed: bool,
) -> None:
    # Arrange
    guard = RagasGuard(
        min_faithfulness=DEFAULT_MIN_FAITHFULNESS,
        min_answer_relevancy=DEFAULT_MIN_RELEVANCY,
        min_context_precision=DEFAULT_MIN_PRECISION,
    )

    # Act
    passed = guard.verify_metrics(metrics)

    # Assert
    assert passed is expected_passed


def test_should_accept_strictly_grounded_report_in_heuristic_evaluation() -> None:
    # Arrange
    guard = RagasGuard(min_faithfulness=DEFAULT_MIN_FAITHFULNESS)
    contexts = [
        "Wymóg formatu .str dla bazy EWMAPA [Załącznik 2, strona 14].",
        "Zamawiający wymaga doświadczenia w modernizacji EGiB.",
    ]
    grounded_answer = (
        "Postępowanie zawiera wymóg formatu .str dla bazy EWMAPA. "
        "Zamawiający wymaga również doświadczenia w modernizacji EGiB."
    )

    # Act
    result = guard.evaluate_claims_grounding(grounded_answer, contexts)

    # Assert
    assert isinstance(result, EvaluationResult)
    assert result.faithfulness >= DEFAULT_MIN_FAITHFULNESS
    assert result.passed is True
    assert result.reason is None


def test_should_reject_hallucinated_claims_not_supported_by_source_contexts() -> None:
    # Arrange
    guard = RagasGuard(min_faithfulness=DEFAULT_MIN_FAITHFULNESS)
    contexts = [
        "Wymóg formatu .str dla bazy EWMAPA [Załącznik 2, strona 14].",
    ]
    hallucinated_answer = (
        "Wymóg formatu .str dla bazy EWMAPA. "
        "Zamawiający żąda wpłacenia wadium w wysokości 10 milionów złotych na konto w Szwajcarii. "
        "Wykonawca musi posiadać własnego satelitę szpiegowskiego na orbicie geostacjonarnej. "
        "Wymagane jest zatrudnienie 500 programistów w języku Fortran."
    )

    # Act
    result = guard.evaluate_claims_grounding(hallucinated_answer, contexts)

    # Assert
    assert result.faithfulness < DEFAULT_MIN_FAITHFULNESS
    assert result.passed is False
    assert "Wskaźnik wierności faktom poniżej wymaganego progu" in (result.reason or "")
    assert len(result.details["unsupported_claims"]) >= 2


def test_should_pass_evaluation_when_answer_is_standard_grounding_refusal() -> None:
    # Arrange
    guard = RagasGuard(min_faithfulness=DEFAULT_MIN_FAITHFULNESS)
    refusal_answer = "Brak informacji w dostarczonej dokumentacji przetargowej."

    # Act
    result = guard.evaluate_claims_grounding(refusal_answer, contexts=["Krótki kontekst."])

    # Assert
    assert result.passed is True
    assert result.faithfulness == 1.0


@pytest.mark.asyncio
async def test_should_evaluate_faithfulness_and_relevancy_using_llm_judge(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mock_ollama = mocker.MagicMock(spec=OllamaClient)
    mock_ollama.generate = mocker.AsyncMock(
        side_effect=[
            "FAITHFULNESS: 0.98\nRELEVANCY: 0.95",
            "FAITHFULNESS: 0.60\nRELEVANCY: 0.90",
        ]
    )
    guard = RagasGuard(min_faithfulness=DEFAULT_MIN_FAITHFULNESS, ollama_client=mock_ollama)

    # Act
    passing_result = await guard.evaluate_with_llm_judge(
        question="Czy wymagany jest format .str?",
        answer="Tak, wymagany jest format .str dla bazy EWMAPA.",
        contexts=["Wymóg formatu .str dla bazy EWMAPA."],
    )
    failing_result = await guard.evaluate_with_llm_judge(
        question="Jakie jest wadium?",
        answer="Wadium wynosi 5 milionów zł.",
        contexts=["Brak informacji o wadium."],
    )

    # Assert
    assert passing_result.faithfulness == 0.98
    assert passing_result.answer_relevancy == 0.95
    assert passing_result.passed is True

    assert failing_result.faithfulness == 0.60
    assert failing_result.passed is False
    assert "Wskaźnik wierności faktom poniżej wymaganego progu" in (failing_result.reason or "")
