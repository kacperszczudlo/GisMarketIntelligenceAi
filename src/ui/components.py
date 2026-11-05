from typing import Any, Dict, List


def render_red_flag_badge(flag_type: str) -> str:
    """Renders styled HTML badge for detected procurement barriers."""
    flag_type_lower = flag_type.lower()

    if "vendor_lockin" in flag_type_lower or "lock-in" in flag_type_lower or "lockin" in flag_type_lower:
        label = "🚨 Vendor Lock-in (.str / format własnościowy)"
        bg_color = "#e53e3e"
        text_color = "#ffffff"
    elif "asymetria" in flag_type_lower or "kary" in flag_type_lower:
        label = "⚖️ Asymetria kar umownych (KIO)"
        bg_color = "#dd6b20"
        text_color = "#ffffff"
    elif "doswiadczenie" in flag_type_lower or "warunki" in flag_type_lower:
        label = "⚠️ Nadmierne warunki udziału"
        bg_color = "#d69e2e"
        text_color = "#ffffff"
    else:
        label = f"ℹ️ {flag_type}"
        bg_color = "#3182ce"
        text_color = "#ffffff"

    return f"""<span style="
        display: inline-block;
        padding: 4px 10px;
        margin: 2px 4px;
        border-radius: 12px;
        background-color: {bg_color};
        color: {text_color};
        font-weight: 600;
        font-size: 0.85rem;
    ">{label}</span>"""


def render_citation_box(citation: str) -> str:
    """Renders prominent citation callout box with document source."""
    return f"""<div style="
        border-left: 4px solid #3182ce;
        background-color: #ebf8ff;
        color: #2b6cb0;
        padding: 10px 14px;
        margin: 8px 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.9rem;
    ">
        <strong>📄 Źródło dowodowe SWZ/OPZ:</strong> {citation}
    </div>"""


def render_kio_warning(risk_level: str) -> str:
    """Renders KIO appeal risk banner."""
    level = risk_level.upper()
    if level in ["HIGH", "WYSOKIE", "KRYTYCZNE"]:
        bg = "#fff5f5"
        border = "#e53e3e"
        color = "#c53030"
        title = "Ryzyko odwołania do KIO: WYSOKIE (Art. 16 / Art. 99 PZP)"
    elif level in ["MEDIUM", "ŚREDNIE"]:
        bg = "#fffaf0"
        border = "#dd6b20"
        color = "#c05621"
        title = "Ryzyko odwołania do KIO: ŚREDNIE"
    else:
        bg = "#f0fff4"
        border = "#38a169"
        color = "#276749"
        title = "Ryzyko odwołania do KIO: NISKIE"

    return f"""<div style="
        border: 1px solid {border};
        background-color: {bg};
        color: {color};
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: 600;
    ">
        🛡️ {title}
    </div>"""


def render_competitor_matrix(competitors: List[Dict[str, Any]]) -> str:
    """Renders HTML comparison table for regional competitors."""
    rows = []
    for c in competitors:
        name = c.get("name", "N/A")
        product = c.get("product", "N/A")
        advantage = c.get("advantage", "N/A")
        rows.append(f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 8px 12px; font-weight: 600;">{name}</td>
                <td style="padding: 8px 12px;">{product}</td>
                <td style="padding: 8px 12px; color: #4a5568;">{advantage}</td>
            </tr>
        """)

    table_rows = "".join(rows)
    return f"""<table style="width: 100%; border-collapse: collapse; margin: 12px 0;">
        <thead>
            <tr style="background-color: #edf2f7; text-align: left;">
                <th style="padding: 8px 12px;">Podmiot konkurencyjny</th>
                <th style="padding: 8px 12px;">Kluczowe oprogramowanie</th>
                <th style="padding: 8px 12px;">Przewaga rynkowa / Bariery</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>"""
