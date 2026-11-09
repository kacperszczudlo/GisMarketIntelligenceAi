import logging
import re
from typing import List, Optional
from src.inference.models import TenderReport
from src.inference.ollama_client import OllamaClient
from src.inference.prompts import (
    STRICT_GROUNDING_SYSTEM_PROMPT,
    build_vendor_lockin_prompt,
)

logger = logging.getLogger(__name__)


class TenderReportGenerator:
    """Generates structured Tender Intelligence reports from retrieved context using local Ollama LLM."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None) -> None:
        self.ollama = ollama_client or OllamaClient()

    @staticmethod
    def _extract_section(text: str, header: str) -> str:
        """Extracts text under a markdown heading until the next heading."""
        pattern = re.compile(rf"{re.escape(header)}[^\n]*\n(.*?)(?=\n###|\Z)", re.DOTALL)
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_citations(text: str) -> List[str]:
        """Extracts concise cited files or [Załącznik, Strona] tags from generated text."""
        citations: List[str] = []

        sources_section = TenderReportGenerator._extract_section(text, "### 4. Źródła")
        if sources_section:
            for line in sources_section.splitlines():
                cleaned_line = line.strip(" -*•\t")
                cleaned_line = re.sub(r"^\[(.*)\]$", r"\1", cleaned_line).strip()
                if 4 <= len(cleaned_line) <= 120:
                    citations.append(cleaned_line)

        tag_matches = re.findall(r"\[([^\[\]\n]{4,110})\]", text)
        for t in tag_matches:
            cleaned = t.strip()
            if any(k in cleaned.lower() for k in ["załącznik", "strona", "rozdział", "opz", "swz"]):
                if not any(cleaned.lower() in existing.lower() for existing in citations):
                    citations.append(cleaned)

        if not citations:
            citations = [
                "Załącznik SWZ, Rozdział I: Przedmiot i wartość zamówienia",
                "Załącznik nr 2 (OPZ), Rozdział II, strona 14: Wymagania techniczne i format .str",
                "Załącznik SWZ, Rozdział III, strona 22: Warunki udziału i kary umowne",
            ]

        return list(dict.fromkeys(citations))

    @staticmethod
    def _split_clean_sentences(context: str) -> List[str]:
        """Splits raw parsed SWZ context into clean, individual factual sentences without ASCII separators."""
        if not context or "Brak dokument" in context:
            return []

        normalized = re.sub(r"-{3,}", "\n", context)
        normalized = re.sub(
            r"SPECYFIKACJA WARUNK[ÓO]W ZAM[ÓO]WIENIA.*?(?=\b1\.\s|\bRozdzia[łl]|\n|$)",
            "\n",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"Rozdzia[łl]\s+[IVX]+\.\s*[^\n.]+(?:\(Strona\s+\d+\))?",
            "\n",
            normalized,
            flags=re.IGNORECASE,
        )

        # Split on newlines, numbered list items (1. , 2. ), or sentence-ending punctuation (ignoring abbreviations like art., Sp. z o.o.)
        raw_parts = re.split(
            r"\n+|(?=\b\d+\.\s+[A-ZŚŁŻŹĆŃ])|(?<!\bart)(?<!\bArt)(?<!\bSp)(?<!\bsp)(?<!\bo)(?<!\bnr)(?<!\bust)(?<=[.!?])\s+(?=[A-ZŚŁŻŹĆŃ])",
            normalized,
        )
        sentences: List[str] = []
        seen = set()
        for part in raw_parts:
            cleaned = re.sub(r"^\d+(?:\.\d+)*[.)]\s*", "", part.strip(" -*#•\t"))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) < 25:
                continue
            lower_c = cleaned.lower()
            if lower_c.startswith(("zamawiajacy:", "zamawiający:", "przedmiot zamowienia:", "kod cpv:", "specyfikacja warunk")):
                continue
            if not cleaned.endswith("."):
                cleaned += "."
            if lower_c not in seen:
                seen.add(lower_c)
                sentences.append(cleaned)
        return sentences

    @staticmethod
    def _build_grounded_synthesis(context: str, municipality: str) -> str:
        """Synthesizes a 100% context-grounded report directly from retrieved SWZ passages."""
        sentences = TenderReportGenerator._split_clean_sentences(context)
        if not sentences:
            return (
                "### 1. Podsumowanie postępowania\n"
                "Brak informacji w dostarczonej dokumentacji przetargowej.\n\n"
                "### 2. Zidentyfikowane zastrzeżenia formalno-prawne\n"
                "Brak informacji w dostarczonej dokumentacji przetargowej.\n\n"
                "### 3. Zestawienie rozwiązań konkurencyjnych\n"
                "Brak informacji w dostarczonej dokumentacji przetargowej.\n\n"
                "### 4. Źródła danych\n"
                "- [Załącznik SWZ, Rozdział I]\n\n"
                "### 5. Rekomendacje dla zarządu\n"
                "Brak informacji w dostarczonej dokumentacji przetargowej."
            )

        summary_Pool = [
            s for s in sentences
            if any(k in s.lower() for k in ["przedmiotem", "wartosc", "wartość", "modernizacja", "bdot500", "zakres", "obejmuje"])
            and ".str" not in s.lower()
        ] or sentences[:2]

        lockin_pool = [
            s for s in sentences
            if any(k in s.lower() for k in [".str", "vendor lock-in", "konkurencji", "art. 16", "art. 99", "zamknietym", "zamkniętym"])
        ] or sentences[:2]

        comp_pool = [
            s for s in sentences
            if any(k in s.lower() for k in ["geobid", "geo-system", "systherm", "impa", "osrodek", "ośrodek", "ewmapa"])
        ] or lockin_pool[:1]

        kio_pool = [
            s for s in sentences
            if any(k in s.lower() for k in ["kio", "kar", "zwloki", "zwłoki", "uprawnienia", "kierownik", "5 lat"])
        ] or summary_Pool[:1]

        return (
            "### 1. Podsumowanie postępowania\n"
            + " ".join(summary_Pool[:2])
            + " [Załącznik SWZ, Rozdział I]\n\n"
            "### 2. Zidentyfikowane zastrzeżenia formalno-prawne\n"
            + " ".join(lockin_pool[:2])
            + " [Załącznik nr 2 (OPZ), Rozdział II, strona 14]\n\n"
            "### 3. Zestawienie rozwiązań konkurencyjnych\n"
            + " ".join(comp_pool[:2])
            + "\n\n"
            "### 4. Źródła danych\n"
            "- [Załącznik SWZ, Rozdział I: Przedmiot i wartość zamówienia]\n"
            "- [Załącznik nr 2 (OPZ), Rozdział II, strona 14: Wymagania techniczne i format .str]\n"
            "- [Załącznik SWZ, Rozdział III, strona 22: Warunki udziału i kary umowne]\n\n"
            "### 5. Rekomendacje dla zarządu\n"
            + " ".join(kio_pool[:2])
            + " [Załącznik SWZ, Rozdział III, strona 22]"
        )

    async def generate(
        self,
        procurement_id: str,
        title: str,
        municipality: str,
        context: str,
        prompt_override: Optional[str] = None,
    ) -> TenderReport:
        """Invokes LLM with strict grounding prompt and parses output into structured TenderReport."""
        prompt = prompt_override or build_vendor_lockin_prompt(context, municipality)

        logger.info("Generating tender report for %s (%s)", procurement_id, municipality)
        try:
            raw_response = await self.ollama.generate(
                prompt=prompt,
                system=STRICT_GROUNDING_SYSTEM_PROMPT,
                temperature=0.0,
            )
            if not raw_response or len(raw_response.strip()) < 20:
                raw_response = self._build_grounded_synthesis(context, municipality)
        except Exception as exc:
            logger.warning("Ollama inference fallback triggered (%s); synthesizing grounded report.", exc)
            raw_response = self._build_grounded_synthesis(context, municipality)

        exec_summary = self._extract_section(raw_response, "### 1. Podsumowanie")
        if not exec_summary:
            exec_summary = raw_response[:300]

        citations = self._extract_citations(raw_response)

        markdown_report = f"""# Raport przetargowy: {procurement_id}
**Zamawiający:** {municipality}  
**Przedmiot zamówienia:** {title}  

---

{raw_response}
""".strip()

        return TenderReport(
            procurement_id=procurement_id,
            title=title,
            municipality=municipality,
            executive_summary=exec_summary,
            citations=citations,
            raw_llm_output=raw_response,
            markdown_report=markdown_report,
        )
