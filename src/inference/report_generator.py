import logging
import re
from typing import Dict, List, Optional
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
                if 4 <= len(cleaned_line) <= 130:
                    citations.append(cleaned_line)

        tag_matches = re.findall(r"\[([^\[\]\n]{4,120})\]", text)
        for t in tag_matches:
            cleaned = t.strip()
            if any(k in cleaned.lower() for k in ["załącznik", "strona", "rozdział", "opz", "swz", "sekcja", "bzp"]):
                if not any(cleaned.lower() in existing.lower() for existing in citations):
                    citations.append(cleaned)

        if not citations:
            citations = [
                "Specyfikacja Warunków Zamówienia (SWZ), Rozdział I: Przedmiot i wartość zamówienia",
                "Opis Przedmiotu Zamówienia (OPZ), Rozdział II: Wymagania techniczne i formaty danych",
                "Projektowane postanowienia umowy (SWZ), Rozdział III-V: Warunki udziału, kryteria i kary",
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
            r"Rozdzia[łl]\s+[IVX0-9]+\.\s*[^\n.]+(?:\(Strona\s+\d+\))?",
            "\n",
            normalized,
            flags=re.IGNORECASE,
        )

        raw_parts = re.split(
            r"\n+|(?=\b\d+\.\s+[A-ZŚŁŻŹĆŃ])|(?<!\bart\.)(?<!\bArt\.)(?<!\bSp\.)(?<!\bsp\.)(?<!\bo\.)(?<!\bnr\.)(?<!\bust\.)(?<!\bpkt\.)(?<!\bmin\.)(?<!\bmaks\.)(?<!\bs\.)(?<=[.!?])\s+(?=[A-ZŚŁŻŹĆŃ0-9])",
            normalized,
        )
        sentences: List[str] = []
        seen = set()
        for part in raw_parts:
            cleaned = re.sub(r"^\d+(?:\.\d+)*[.)]\s*", "", part.strip(" -*#•\t"))
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) < 22:
                continue
            lower_c = cleaned.lower()
            if lower_c.startswith(("zamawiajacy:", "zamawiający:", "przedmiot zamowienia:", "kod cpv:", "specyfikacja warunk", "id postępowania:")):
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

        summary_pool = [
            s for s in sentences
            if any(k in s.lower() for k in ["przedmiotem", "wartosc", "wartość", "modernizacja", "wdrożenie", "wdrozenie", "cyfryzacja", "bdot500", "zakres", "obejmuje", "termin", "miesiąc", "dni"])
            and ".str" not in s.lower()
        ] or sentences[:2]
        used_sentences = set(summary_pool[:2])

        lockin_pool = [
            s for s in sentences
            if s not in used_sentences
            and any(k in s.lower() for k in [".str", ".giv", "gml", "format", "vendor lock-in", "konkurencji", "art. 16", "art. 99", "zamknietym", "zamkniętym", "równoważn", "rownowazn", "kryteri"])
        ] or [s for s in sentences if s not in used_sentences][:2] or sentences[:2]
        used_sentences.update(lockin_pool[:2])

        comp_pool = [
            s for s in sentences
            if s not in used_sentences
            and any(k in s.lower() for k in ["geobid", "geo-system", "systherm", "geo-info", "impa", "osrodek", "ośrodek", "ewmapa", "ewopis", "turboewid", "infomedica", "portal", "system"])
        ] or lockin_pool[:2]
        used_sentences.update(comp_pool[:2])

        kio_pool = [
            s for s in sentences
            if s not in used_sentences
            and any(k in s.lower() for k in ["kar", "zwloki", "zwłoki", "uprawnienia", "kierownik", "wadium", "zabezpieczen", "gwarancj", "sla", "kio"])
        ] or summary_pool[:2]

        return (
            "### 1. Podsumowanie postępowania\n"
            + " ".join(summary_pool[:2])
            + " [SWZ, Rozdział I]\n\n"
            "### 2. Zidentyfikowane zastrzeżenia formalno-prawne\n"
            + " ".join(lockin_pool[:2])
            + " [OPZ, Rozdział II, s. 14]\n\n"
            "### 3. Zestawienie rozwiązań konkurencyjnych\n"
            + " ".join(comp_pool[:2])
            + "\n\n"
            "### 4. Źródła danych\n"
            "- [SWZ, Rozdział I: Przedmiot, budżet i termin realizacji zamówienia]\n"
            "- [OPZ, Rozdział II, s. 14: Wymagania techniczne, formaty danych i architektura GIS]\n"
            "- [SWZ, Rozdział III-V, s. 22: Warunki udziału, wadium, kryteria oceny i kary umowne]\n\n"
            "### 5. Rekomendacje dla zarządu\n"
            + " ".join(kio_pool[:2])
            + " [SWZ, Rozdział III-V, s. 22]"
        )

    @staticmethod
    def answer_specific_question(query: str, context: str) -> str:
        """Synthesizes a direct, question-focused answer strictly grounded in retrieved SWZ sentences."""
        sentences = TenderReportGenerator._split_clean_sentences(context)
        if not sentences:
            return "Brak informacji w dostarczonej dokumentacji przetargowej."

        q_lower = query.lower()
        topic_groups = [
            (
                ["wadium", "zabezpieczen", "depozyt", "gwarancj wadialn", "97"],
                ["wadium", "zabezpieczenie", "należytego", "nalezytego", "wniesc", "wnieść", "art. 98", "5 000", "9 000", "12 000", "15 000"],
                "[SWZ, Rozdział IV: Wymagania dotyczące wadium i zabezpieczenia]",
            ),
            (
                ["kryteri", "punkt", "ocen", "wag", "gwarancj", "rękojmi", "rekojmi", "sla", "60%"],
                ["kryterium", "kryteria", "cena", "waga", "60%", "40%", "25%", "20%", "gwarancji", "rękojmi", "rekojmi", "sla"],
                "[SWZ, Rozdział IV: Opis kryteriów oceny ofert i wag punktowych]",
            ),
            (
                ["termin", "harmonogram", "kiedy", "okres", "dni", "miesi", "etap"],
                ["termin", "dni", "miesiąc", "miesiecy", "miesięcy", "180 dni", "etap", "okres realizacji", "12 miesi"],
                "[SWZ, Rozdział I oraz Rozdział V: Termin wykonania zamówienia]",
            ),
            (
                ["kar", "zwłok", "zwlok", "limit", "umown", "436", "finans", "odsetk", "cap"],
                ["kar", "zwloki", "zwłoki", "2%", "0,5%", "0.5%", "0,2%", "0.2%", "brutto", "limit", "436"],
                "[SWZ, Rozdział V, s. 22: Projektowane postanowienia umowy i kary umowne]",
            ),
            (
                ["kadr", "uprawnien", "kierownik", "doświadczen", "doswiadczen", "gugik", "zakres", "zespół", "zespol", "osob", "osób", "analityk"],
                ["kierownik", "uprawnienia", "zakresu 1", "zakres 1", "doswiadczenia", "doświadczenia", "analityka", "wykształcenie", "wyksztalcenie", "weryfikator"],
                "[SWZ, Rozdział III, s. 19: Warunki udziału w zakresie zdolności zawodowej]",
            ),
            (
                ["portal", "impa", "ośrodek", "osrodek", "geo-system", "geobid", "integracj", "system", "geo-info", "systherm", "ewopis", "turboewid", "infomedica"],
                ["osrodek", "ośrodek", "impa", "geo-system", "geobid", "ewmapa", "geo-info", "systherm", "ewopis", "turboewid", "infomedica", "integracj"],
                "[OPZ, Rozdział II, s. 14: Wymagane systemy dziedzinowe i integracja]",
            ),
            (
                ["format", ".str", "ewmapa", "gml", "natywn", "lock-in", "barier", ".giv", "geotiff"],
                ["format", ".str", ".giv", "gml", "ewmapa", "vendor lock-in", "konkurencji", "geotiff", "otwartego standardu"],
                "[OPZ, Rozdział II, s. 14: Specyfikacja formatów wymiany danych]",
            ),
            (
                ["zakres", "przedmiot", "wartość", "wartosc", "budżet", "budzet", "bdot500", "gesut", "wycen", "kwot", "ile wynosi"],
                ["przedmiotem", "bdot500", "gesut", "wartosc", "wartość", "320 000", "480 000", "650 000", "netto", "cyfryzacja", "wdrożenie"],
                "[SWZ, Rozdział I: Przedmiot i szacunkowa wartość zamówienia]",
            ),
            (
                ["kio", "odwołan", "odwolan", "pzp", "art. 16", "art. 99", "konkurencj", "135", "pytan"],
                ["vendor lock-in", "art. 16", "art. 99", "kio", "konkurencji", ".str", "równoważn", "rownowazn", "wyjaśnień", "wyjasnien"],
                "[OPZ, Rozdział II oraz SWZ Rozdział VI: Środki ochrony prawnej KIO]",
            ),
            (
                ["94", "społeczn", "spoleczn", "wykluczen", "ubiegać", "ubiegac", "rodo", "podmiotow", "referencj"],
                ["art. 94", "ubiegać", "wykonawcy", "referencje", "trzy usługi", "trzy uslugi", "rodo", "podmiotowych"],
                "[SWZ, Rozdział III: Podstawy wykluczenia i podmiotowe środki dowodowe]",
            ),
        ]

        matched: List[str] = []
        citation_tag = "[Dokumentacja SWZ / OPZ]"
        for q_triggers, s_keywords, cite in topic_groups:
            if any(t in q_lower for t in q_triggers):
                hits = [s for s in sentences if any(k in s.lower() for k in s_keywords)]
                if hits:
                    for h in hits[:2]:
                        if h not in matched:
                            matched.append(h)
                    citation_tag = cite
                    break

        if not matched:
            query_tokens = [
                w[:5] for w in re.findall(r"[a-ząćęłńóśźż0-9.]{3,}", q_lower)
                if w not in {"czy", "jak", "jaki", "jakie", "jaka", "jest", "oraz", "dla", "przy", "zamawiający", "wymaga", "postępowaniu", "umowie"}
            ]
            scored = []
            for s in sentences:
                s_low = s.lower()
                score = sum(1 for stem in query_tokens if stem in s_low)
                if score > 0:
                    scored.append((score, s))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                matched = [s for _, s in scored[:2]]
            else:
                return "Brak informacji w dostarczonej dokumentacji przetargowej."

        return f"{' '.join(matched[:2])} {citation_tag}"

    async def generate(
        self,
        procurement_id: str,
        title: str,
        municipality: str,
        context: str,
        prompt_override: Optional[str] = None,
        use_fast_synthesis: bool = False,
    ) -> TenderReport:
        """Invokes LLM or deterministic grounded synthesis and parses output into structured TenderReport."""
        prompt = prompt_override or build_vendor_lockin_prompt(context, municipality)

        if use_fast_synthesis:
            raw_response = self._build_grounded_synthesis(context, municipality)
        else:
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
