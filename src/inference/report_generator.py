import logging
import re
from typing import List, Optional
from src.inference.models import CompetitorItem, RedFlagItem, TenderReport
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
        """Extracts cited files or [Załącznik, Strona] tags from generated text."""
        citations = []
        # Match [Załącznik ..., Strona ...]
        tag_matches = re.findall(r"\[(.*?)\]", text)
        for t in tag_matches:
            if any(k in t.lower() for k in ["załącznik", "strona", "rozdział", "opz", "swz"]):
                citations.append(t.strip())

        # Match bulleted lines in sources section
        source_lines = re.findall(r"[-*]\s+([^\n]+)", text)
        for s in source_lines:
            if any(ext in s.lower() for ext in [".pdf", ".docx", ".str", "kio", "załącznik"]):
                citations.append(s.strip())

        return list(dict.fromkeys(citations))

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
        raw_response = await self.ollama.generate(
            prompt=prompt,
            system=STRICT_GROUNDING_SYSTEM_PROMPT,
            temperature=0.0,
        )

        exec_summary = self._extract_section(raw_response, "### 1. Podsumowanie")
        if not exec_summary:
            exec_summary = raw_response[:300]

        citations = self._extract_citations(raw_response)

        # Build clean formatted Markdown report
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
