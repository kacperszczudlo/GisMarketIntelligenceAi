"""Unicode-safe multi-page PDF exporter using fpdf2 with TrueType Polish font support."""

from pathlib import Path
import re
from typing import Optional, Tuple

from fpdf import FPDF


def _find_unicode_fonts() -> Tuple[Optional[str], Optional[str]]:
    """Finds a system TrueType font pair (regular, bold) supporting Polish diacritics."""
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for reg, bold in candidates:
        if Path(reg).exists():
            return reg, (bold if Path(bold).exists() else reg)
    return None, None


class _TenderAuditPDF(FPDF):
    """Custom FPDF layout with clean header/footer for PZP & GIS audit reports."""

    def __init__(self, font_family: str) -> None:
        super().__init__(format="A4", unit="mm")
        self._font_family_name = font_family
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 16, 16)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font(self._font_family_name, size=8)
        self.set_text_color(110, 118, 129)
        self.cell(0, 6, f"Strona {self.page_no()}/{{nb}} | GisMarket Intelligence AI", align="L")


def export_report_to_pdf_bytes(markdown_report: str) -> bytes:
    """Renders a Markdown procurement audit report into valid multi-page UTF-8 PDF bytes."""
    reg_font, bold_font = _find_unicode_fonts()
    use_unicode = reg_font is not None
    family = "PolishSans" if use_unicode else "Helvetica"

    pdf = _TenderAuditPDF(font_family=family)
    pdf.pdf_version = "1.4"
    pdf.alias_nb_pages()

    if use_unicode and reg_font and bold_font:
        pdf.add_font(family, "", reg_font)
        pdf.add_font(family, "B", bold_font)

    pdf.add_page()
    text = (markdown_report or "Brak treści raportu.").strip()

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        if stripped == "---":
            pdf.set_draw_color(205, 213, 224)
            y = pdf.get_y() + 1.5
            pdf.line(16, y, 194, y)
            pdf.ln(5)
            continue

        is_h1 = stripped.startswith("# ")
        is_heading = stripped.startswith("#")
        clean = re.sub(r"^#{1,6}\s*", "", stripped)
        clean = re.sub(r"\*\*(.*?)\*\*", r"\1", clean)
        clean = re.sub(r"`(.*?)`", r"\1", clean)
        if clean.startswith(("- ", "* ")):
            clean = "• " + clean[2:].strip()

        if not use_unicode:
            clean = clean.translate(str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ–—„”•", "acelnoszzACELNOSZZ--\"\"-"))

        if is_h1:
            pdf.set_font(family, "B", 14)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 7, clean, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif is_heading:
            pdf.ln(2)
            pdf.set_font(family, "B", 11.5)
            pdf.set_text_color(30, 58, 138)
            pdf.multi_cell(0, 6, clean, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        else:
            pdf.set_font(family, "", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 5.4, clean, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
