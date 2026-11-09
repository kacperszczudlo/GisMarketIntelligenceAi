from typing import Any, Dict, List


SVG_ICONS: Dict[str, str] = {
    "layers": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 6px; flex-shrink: 0;">'
        '<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>'
        '<polyline points="2 17 12 22 22 17"></polyline>'
        '<polyline points="2 12 12 17 22 12"></polyline></svg>'
    ),
    "lock": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 6px; flex-shrink: 0;">'
        '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>'
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>'
    ),
    "scale": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 6px; flex-shrink: 0;">'
        '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path>'
        '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path>'
        '<path d="M7 21h10"></path><path d="M12 3v18"></path>'
        '<path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"></path></svg>'
    ),
    "shield_alert": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 8px; flex-shrink: 0;">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>'
        '<line x1="12" y1="8" x2="12" y2="12"></line>'
        '<line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
    ),
    "file_code": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 8px; flex-shrink: 0;">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
        '<polyline points="14 2 14 8 20 8"></polyline>'
        '<line x1="16" y1="13" x2="8" y2="13"></line>'
        '<line x1="16" y1="17" x2="8" y2="17"></line></svg>'
    ),
    "check_circle": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 8px; flex-shrink: 0;">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>'
        '<polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
    ),
    "cpu": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 8px; flex-shrink: 0;">'
        '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>'
        '<rect x="9" y="9" width="6" height="6"></rect>'
        '<line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line>'
        '<line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line>'
        '<line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line>'
        '<line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>'
    ),
    "network": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align: -3px; margin-right: 8px; flex-shrink: 0;">'
        '<rect x="16" y="16" width="6" height="6" rx="1"></rect>'
        '<rect x="2" y="16" width="6" height="6" rx="1"></rect>'
        '<rect x="9" y="2" width="6" height="6" rx="1"></rect>'
        '<path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"></path>'
        '<path d="M12 12V8"></path></svg>'
    ),
    "status_dot": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 16 16" '
        'style="vertical-align: -2px; margin-right: 8px; flex-shrink: 0;">'
        '<circle cx="8" cy="8" r="5" fill="{color}" />'
        '<circle cx="8" cy="8" r="7" fill="none" stroke="{color}" stroke-opacity="0.35" stroke-width="1.5" /></svg>'
    ),
}


def get_svg_icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    """Returns a custom inline SVG icon with no external assets or emojis."""
    template = SVG_ICONS.get(name, SVG_ICONS["layers"])
    return template.format(size=size, color=color)


def get_glassmorphism_stylesheet() -> str:
    """Returns global CSS implementing high-contrast dark glassmorphism for the Streamlit workspace."""
    return """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp {
        background-color: #0b0f19;
        background-image:
            radial-gradient(circle at 12% 18%, rgba(56, 189, 248, 0.08), transparent 38%),
            radial-gradient(circle at 88% 12%, rgba(99, 102, 241, 0.08), transparent 42%),
            radial-gradient(circle at 50% 85%, rgba(16, 185, 129, 0.05), transparent 45%);
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.78) !important;
        backdrop-filter: blur(20px) saturate(160%);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .glass-panel {
        background: rgba(17, 24, 39, 0.66);
        backdrop-filter: blur(16px) saturate(150%);
        -webkit-backdrop-filter: blur(16px) saturate(150%);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
    }

    .glass-stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 14px;
        margin: 18px 0 26px 0;
    }

    .glass-stat-card {
        background: rgba(30, 41, 59, 0.52);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 18px;
    }

    .glass-stat-label {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 500;
        margin-bottom: 6px;
    }

    .glass-stat-value {
        font-size: 1.35rem;
        font-weight: 600;
        color: #f8fafc;
        letter-spacing: -0.02em;
    }

    .tender-row-card {
        background: rgba(17, 24, 39, 0.62);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        transition: border-color 180ms ease, background 180ms ease;
    }

    .tender-row-card:hover {
        border-color: rgba(56, 189, 248, 0.35);
        background: rgba(30, 41, 59, 0.68);
    }

    .tender-title {
        font-size: 1.02rem;
        font-weight: 600;
        color: #f8fafc;
        line-height: 1.45;
        margin-bottom: 8px;
    }

    .tender-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        font-size: 0.84rem;
        color: #cbd5e1;
    }

    .mono-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        padding: 3px 8px;
        border-radius: 6px;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #38bdf8;
    }

    .meta-pill {
        padding: 3px 10px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
        font-size: 0.8rem;
    }

    .stButton > button[kind="primary"] {
        background: rgba(14, 165, 233, 0.88) !important;
        border: 1px solid rgba(56, 189, 248, 0.45) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 0.55rem 1.25rem !important;
        transition: background 180ms ease, border-color 180ms ease !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: rgba(2, 132, 199, 0.96) !important;
        border-color: rgba(125, 211, 252, 0.75) !important;
    }
    </style>"""


def render_red_flag_badge(flag_type: str) -> str:
    """Renders a glassmorphic badge with custom SVG icon for detected procurement barriers."""
    flag_type_lower = flag_type.lower()

    if "vendor_lockin" in flag_type_lower or "lock-in" in flag_type_lower or "lockin" in flag_type_lower:
        icon = get_svg_icon("lock", size=14, color="#fca5a5")
        label = "Vendor Lock-in: wymóg natywnego formatu .str"
        bg_color = "rgba(229, 62, 62, 0.16)"
        border_color = "#e53e3e"
        text_color = "#fecaca"
    elif "asymetria" in flag_type_lower or "kary" in flag_type_lower:
        icon = get_svg_icon("scale", size=14, color="#fdba74")
        label = "Asymetria kar umownych w SWZ"
        bg_color = "rgba(221, 107, 32, 0.16)"
        border_color = "#dd6b20"
        text_color = "#fed7aa"
    elif "doswiadczenie" in flag_type_lower or "warunki" in flag_type_lower:
        icon = get_svg_icon("shield_alert", size=14, color="#fde047")
        label = "Nadmierne warunki udziału w postępowaniu"
        bg_color = "rgba(214, 158, 46, 0.16)"
        border_color = "#d69e2e"
        text_color = "#fef08a"
    else:
        icon = get_svg_icon("layers", size=14, color="#93c5fd")
        label = flag_type
        bg_color = "rgba(49, 130, 206, 0.16)"
        border_color = "#3182ce"
        text_color = "#bfdbfe"

    return f"""<span class="red-flag-badge" style="
        display: inline-flex;
        align-items: center;
        padding: 6px 13px;
        margin: 4px 8px 4px 0;
        border-radius: 8px;
        background-color: {bg_color};
        border: 1px solid {border_color};
        color: {text_color};
        font-weight: 500;
        font-size: 0.84rem;
        backdrop-filter: blur(8px);
    ">{icon}{label}</span>"""


def render_citation_box(citation: str) -> str:
    """Renders a glassmorphic citation box with a custom document SVG icon."""
    icon = get_svg_icon("file_code", size=16, color="#38bdf8")
    return f"""<div style="
        border: 1px solid rgba(56, 189, 248, 0.28);
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(12px);
        color: #e2e8f0;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 10px;
        font-size: 0.88rem;
        display: flex;
        align-items: center;
    ">
        {icon}<span><strong style="color: #7dd3fc;">Źródło dowodowe SWZ/OPZ:</strong> {citation}</span>
    </div>"""


def render_kio_warning(risk_level: str) -> str:
    """Renders a glassmorphic KIO appeal risk callout with a custom SVG shield icon."""
    level = risk_level.upper()
    if level in ["HIGH", "WYSOKIE", "KRYTYCZNE"]:
        bg = "rgba(153, 27, 27, 0.22)"
        border = "rgba(248, 113, 113, 0.45)"
        color = "#fecaca"
        icon_color = "#f87171"
        title = "Ryzyko odwołania do KIO: WYSOKIE (podstawa: art. 16 oraz art. 99 PZP)"
    elif level in ["MEDIUM", "ŚREDNIE"]:
        bg = "rgba(154, 52, 18, 0.22)"
        border = "rgba(251, 146, 60, 0.45)"
        color = "#fed7aa"
        icon_color = "#fb923c"
        title = "Ryzyko odwołania do KIO: ŚREDNIE"
    else:
        bg = "rgba(22, 101, 52, 0.22)"
        border = "rgba(74, 222, 128, 0.45)"
        color = "#bbf7d0"
        icon_color = "#4ade80"
        title = "Ryzyko odwołania do KIO: NISKIE"

    icon = get_svg_icon("shield_alert", size=18, color=icon_color)
    return f"""<div style="
        border: 1px solid {border};
        background: {bg};
        backdrop-filter: blur(12px);
        color: {color};
        padding: 13px 18px;
        border-radius: 10px;
        margin: 12px 0;
        font-weight: 500;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
    ">
        {icon}<span>{title}</span>
    </div>"""


def render_competitor_matrix(competitors: List[Dict[str, Any]]) -> str:
    """Renders a clean glassmorphic table for regional competitors."""
    rows = []
    for c in competitors:
        name = c.get("name", "N/A")
        product = c.get("product", "N/A")
        advantage = c.get("advantage", "N/A")
        rows.append(
            f'<tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.07);">'
            f'<td style="padding: 12px 14px; font-weight: 600; color: #f8fafc;">{name}</td>'
            f'<td style="padding: 12px 14px; color: #38bdf8; font-family: \'JetBrains Mono\', monospace; font-size: 0.83rem;">{product}</td>'
            f'<td style="padding: 12px 14px; color: #cbd5e1;">{advantage}</td>'
            f"</tr>"
        )

    table_rows = "".join(rows)
    return f"""<div style="
        background: rgba(17, 24, 39, 0.65);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 12px;
        overflow: hidden;
        margin: 12px 0;
    ">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem;">
            <thead>
                <tr style="background: rgba(30, 41, 59, 0.75); text-align: left; color: #94a3b8; font-size: 0.78rem;">
                    <th style="padding: 10px 14px; font-weight: 600;">Podmiot konkurencyjny</th>
                    <th style="padding: 10px 14px; font-weight: 600;">Rozwiązanie bazodanowe</th>
                    <th style="padding: 10px 14px; font-weight: 600;">Pozycja w postępowaniu</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>"""


def render_tender_card(
    ocds_id: str,
    title: str,
    municipality: str,
    voivodeship: str,
    budget_pln: float,
    status: str,
) -> str:
    """Renders an individual tender notice as a readable, non-truncated glass card."""
    budget_str = f"{budget_pln:,.0f} PLN".replace(",", " ") if budget_pln > 0 else "Budżet wg SWZ"
    return f"""<div class="tender-row-card">
        <div class="tender-title">{title}</div>
        <div class="tender-meta-row">
            <span class="mono-pill">{ocds_id}</span>
            <span class="meta-pill">Zamawiający: {municipality}</span>
            <span class="meta-pill">Województwo: {voivodeship}</span>
            <span class="meta-pill">Szacunek: {budget_str}</span>
            <span class="meta-pill">{status}</span>
        </div>
    </div>"""
