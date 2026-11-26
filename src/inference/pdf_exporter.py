"""Pure-Python multi-page PDF-1.4 exporter for Tender Intelligence reports."""

import re
import textwrap
from typing import List, Tuple

_POLISH_TRANS = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ–—„”•",
    "acelnoszzACELNOSZZ--\"\"-",
)

LINES_PER_PAGE = 46
WRAP_WIDTH = 86


def _normalize_pdf_text(text: str) -> str:
    clean = text.translate(_POLISH_TRANS)
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _markdown_to_wrapped_lines(markdown_text: str) -> List[Tuple[str, bool]]:
    """Converts markdown report text into wrapped (line_text, is_heading) tuples."""
    result: List[Tuple[str, bool]] = []
    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            result.append(("", False))
            continue
        if stripped == "---":
            result.append(("-" * 72, False))
            continue

        is_heading = stripped.startswith("#")
        clean = re.sub(r"^#{1,6}\s*", "", stripped)
        clean = re.sub(r"\*\*(.*?)\*\*", r"\1", clean)
        clean = re.sub(r"`(.*?)`", r"\1", clean)
        if clean.startswith(("- ", "* ")):
            clean = "- " + clean[2:].strip()

        wrapped = textwrap.wrap(clean, width=WRAP_WIDTH) or [""]
        for w in wrapped:
            result.append((w, is_heading))
    return result


def export_report_to_pdf_bytes(markdown_report: str) -> bytes:
    """Renders a Markdown procurement audit report into valid multi-page PDF-1.4 bytes."""
    lines = _markdown_to_wrapped_lines(markdown_report or "Brak tresci raportu.")
    pages: List[List[Tuple[str, bool]]] = [
        lines[i : i + LINES_PER_PAGE] for i in range(0, max(1, len(lines)), LINES_PER_PAGE)
    ]

    # Object 1: Catalog, Object 2: Pages, Object 3: Regular Font, Object 4: Bold Font
    objects: List[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"",  # Placeholder for Pages object
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n",
    ]

    page_obj_ids: List[int] = []
    next_id = 5

    for page_idx, page_lines in enumerate(pages, 1):
        content_ops = ["BT", "50 790 Td", "14 TL"]
        for line_idx, (line_text, is_heading) in enumerate(page_lines):
            font_op = "/F2 11 Tf" if is_heading else "/F1 10 Tf"
            escaped = _normalize_pdf_text(line_text)
            if line_idx == 0:
                content_ops.append(f"{font_op} ({escaped}) Tj")
            else:
                content_ops.append(f"T* {font_op} ({escaped}) Tj")

        # Footer with page number
        footer = _normalize_pdf_text(f"Strona {page_idx}/{len(pages)} | GisMarket Intelligence AI")
        content_ops.append(f"ET\nBT /F1 8 Tf 50 32 Td ({footer}) Tj ET")
        stream_data = "\n".join(content_ops).encode("latin-1", errors="ignore")

        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        page_obj_ids.append(page_id)

        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n".encode("ascii")
        )
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii")
            + stream_data
            + b"\nendstream\nendobj\n"
        )

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>\nendobj\n".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
