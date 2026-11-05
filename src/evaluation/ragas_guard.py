import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.inference.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Evaluation result for RAG output verification."""
    faithfulness: float
    answer_relevancy: float = 1.0
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    passed: bool = False
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class RagasGuard:
    """Continuous Quality Gate enforcing faithfulness and answer relevancy thresholds."""

    def __init__(
        self,
        min_faithfulness: float = 0.95,
        min_answer_relevancy: float = 0.80,
        min_context_precision: float = 0.70,
        ollama_client: Optional[OllamaClient] = None,
    ) -> None:
        self.min_faithfulness = min_faithfulness
        self.min_answer_relevancy = min_answer_relevancy
        self.min_context_precision = min_context_precision
        self.ollama = ollama_client or OllamaClient()

    def verify_metrics(self, metrics: Dict[str, float]) -> bool:
        """Verifies if given metric dictionary satisfies quality gate thresholds."""
        faithfulness = metrics.get("faithfulness", 0.0)
        if faithfulness < self.min_faithfulness:
            logger.warning(
                "Faithfulness %.4f failed quality gate (min: %.2f)",
                faithfulness,
                self.min_faithfulness,
            )
            return False

        if "answer_relevancy" in metrics:
            relevancy = metrics["answer_relevancy"]
            if relevancy < self.min_answer_relevancy:
                logger.warning(
                    "Answer relevancy %.4f failed quality gate (min: %.2f)",
                    relevancy,
                    self.min_answer_relevancy,
                )
                return False

        if "context_precision" in metrics and self.min_context_precision is not None:
            precision = metrics["context_precision"]
            if precision < self.min_context_precision:
                logger.warning(
                    "Context precision %.4f failed quality gate (min: %.2f)",
                    precision,
                    self.min_context_precision,
                )
                return False

        return True

    @staticmethod
    def _extract_sentences(text: str) -> List[str]:
        """Splits markdown text into clean factual statements."""
        # Remove headers, bullet markers, markdown bold
        cleaned_lines = []
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("---"):
                continue
            # Strip bullet prefixes
            line_str = re.sub(r"^[-*•\d+.]\s*", "", line_str)
            cleaned_lines.append(line_str)

        full_text = " ".join(cleaned_lines)
        # Split by sentence terminators
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def evaluate_claims_grounding(
        self,
        answer: str,
        contexts: List[str],
        question: Optional[str] = None,
    ) -> EvaluationResult:
        """Heuristic lexical and entity verification of answer claims against context chunks."""
        statements = self._extract_sentences(answer)
        if not statements:
            return EvaluationResult(
                faithfulness=1.0,
                answer_relevancy=1.0,
                passed=True,
                reason="Brak twierdzeń do weryfikacji.",
            )

        merged_context = " ".join(contexts).lower()
        supported_claims = []
        unsupported_claims = []

        stop_words = {
            "w", "z", "o", "i", "a", "na", "do", "oraz", "dla", "jest", "są",
            "to", "że", "się", "nie", "jak", "od", "po", "przez", "ze", "we",
            "lub", "albo", "postępowanie", "zamawiający", "wykonawca",
        }

        for stmt in statements:
            words = [
                re.sub(r"[^\w]", "", w.lower())
                for w in stmt.split()
                if len(re.sub(r"[^\w]", "", w)) >= 3
            ]
            key_words = [w for w in words if w not in stop_words]

            if not key_words:
                supported_claims.append(stmt)
                continue

            # Check matching keywords in context
            matches = [w for w in key_words if w in merged_context]
            match_ratio = len(matches) / len(key_words)

            # A statement is deemed grounded if >= 60% of significant content words are supported
            if match_ratio >= 0.60:
                supported_claims.append(stmt)
            else:
                unsupported_claims.append(stmt)

        faithfulness = len(supported_claims) / len(statements)
        passed = faithfulness >= self.min_faithfulness

        reason = None
        if not passed:
            reason = (
                f"Wskaźnik wierności faktom poniżej wymaganego progu {self.min_faithfulness}: "
                f"{faithfulness:.4f}. Niepotwierdzone twierdzenia: {len(unsupported_claims)}"
            )

        return EvaluationResult(
            faithfulness=faithfulness,
            answer_relevancy=1.0,
            passed=passed,
            reason=reason,
            details={
                "total_claims": len(statements),
                "supported_claims": supported_claims,
                "unsupported_claims": unsupported_claims,
            },
        )

    async def evaluate_with_llm_judge(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> EvaluationResult:
        """Uses local Ollama LLM as a semantic judge to evaluate faithfulness and relevancy."""
        judge_prompt = f"""Oceń bezwzględnie wierność odpowiedzi (Faithfulness) w skali 0.0 do 1.0 na podstawie podanego kontekstu.
Kontekst źródłowy:
{chr(10).join(contexts)}

Pytanie:
{question}

Odpowiedź do oceny:
{answer}

Zasady oceny:
1. Każde zdanie w odpowiedzi musi mieć bezpośrednie potwierdzenie w kontekście.
2. Jakakolwiek halucynacja lub ekstrapolacja obniża ocenę.
Odpowiedz wyłącznie w formacie jednej linii:
FAITHFULNESS: <liczba_od_0.0_do_1.0>
RELEVANCY: <liczba_od_0.0_do_1.0>
"""
        response = await self.ollama.generate(prompt=judge_prompt, temperature=0.0)

        faith_match = re.search(r"FAITHFULNESS:\s*([\d.]+)", response, re.IGNORECASE)
        rel_match = re.search(r"RELEVANCY:\s*([\d.]+)", response, re.IGNORECASE)

        faithfulness = float(faith_match.group(1)) if faith_match else 0.0
        relevancy = float(rel_match.group(1)) if rel_match else 0.0

        passed = self.verify_metrics({
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
        })

        reason = None
        if not passed:
            reason = (
                f"Wskaźnik wierności faktom poniżej wymaganego progu {self.min_faithfulness}: "
                f"{faithfulness:.4f}"
            )

        return EvaluationResult(
            faithfulness=faithfulness,
            answer_relevancy=relevancy,
            passed=passed,
            reason=reason,
            details={"raw_judge_output": response},
        )
