import html
import re
from typing import Dict, List


def _compact_html(raw_html: str) -> str:
    """Removes line-leading indentation so Streamlit's CommonMark parser never treats HTML as a code block."""
    return "\n".join(line.strip() for line in raw_html.strip().splitlines() if line.strip())


def get_svg_icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    """Returns clean, custom inline SVG vector icons sized strictly on the ui-scale-architecture grid (16, 20, 24, 32, 48)."""
    allowed_sizes = {16, 20, 24, 32, 48}
    resolved_size = size if size in allowed_sizes else 20
    icons: Dict[str, str] = {
        "layers": (
            '<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>'
            '<polyline points="2 17 12 22 22 17"></polyline>'
            '<polyline points="2 12 12 17 22 12"></polyline>'
        ),
        "shield-alert": (
            '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>'
            '<line x1="12" y1="8" x2="12" y2="12"></line>'
            '<line x1="12" y1="16" x2="12.01" y2="16"></line>'
        ),
        "scale": (
            '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path>'
            '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"></path>'
            '<path d="M7 21h10"></path>'
            '<path d="M12 3v18"></path>'
            '<path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"></path>'
        ),
        "file-check": (
            '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>'
            '<polyline points="14 2 14 8 20 8"></polyline>'
            '<path d="m9 15 2 2 4-4"></path>'
        ),
        "sparkles": (
            '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z"></path>'
        ),
        "radar": (
            '<circle cx="12" cy="12" r="9"></circle>'
            '<circle cx="12" cy="12" r="5"></circle>'
            '<circle cx="12" cy="12" r="1"></circle>'
            '<line x1="12" y1="12" x2="18.36" y2="5.64"></line>'
        ),
        "cpu": (
            '<rect x="4" y="4" width="16" height="16" rx="2"></rect>'
            '<rect x="9" y="9" width="6" height="6"></rect>'
            '<path d="M15 2v2"></path><path d="M15 20v2"></path>'
            '<path d="M2 15h2"></path><path d="M2 9h2"></path>'
            '<path d="M20 15h2"></path><path d="M20 9h2"></path>'
            '<path d="M9 2v2"></path><path d="M9 20v2"></path>'
        ),
        "database": (
            '<ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>'
            '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>'
            '<path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path>'
        ),
        "sliders": (
            '<line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line>'
            '<line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line>'
            '<line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line>'
            '<line x1="2" y1="14" x2="6" y2="14"></line>'
            '<line x1="10" y1="8" x2="14" y2="8"></line>'
            '<line x1="18" y1="16" x2="22" y2="16"></line>'
        ),
        "check-circle": (
            '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>'
            '<polyline points="22 4 12 14.01 9 11.01"></polyline>'
        ),
        "building": (
            '<rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>'
            '<path d="M9 22v-4h6v4"></path>'
            '<path d="M8 6h.01"></path><path d="M16 6h.01"></path>'
            '<path d="M12 6h.01"></path><path d="M12 10h.01"></path>'
            '<path d="M12 14h.01"></path><path d="M16 10h.01"></path>'
            '<path d="M16 14h.01"></path><path d="M8 10h.01"></path>'
            '<path d="M8 14h.01"></path>'
        ),
        "map-pin": (
            '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>'
            '<circle cx="12" cy="10" r="3"></circle>'
        ),
        "wallet": (
            '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"></path>'
            '<path d="M3 5v14a2 2 0 0 0 2 2h16v-5"></path>'
            '<path d="M18 12a2 2 0 0 0 0 4h4v-4Z"></path>'
        ),
        "compass": (
            '<circle cx="12" cy="12" r="10"></circle>'
            '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>'
        ),
    }
    body = icons.get(name, icons["layers"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{resolved_size}" height="{resolved_size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.85" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;vertical-align:middle;display:inline-block;">{body}</svg>'
    )


def get_glassmorphism_stylesheet() -> str:
    """Returns true multi-layered Glassmorphism CSS combined with 8pt UI Scale Architecture tokens."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            /* 8pt Spatial Architecture Tokens */
            --space-1: 0.25rem;  /* 4px micro */
            --space-2: 0.5rem;   /* 8px */
            --space-3: 1rem;     /* 16px */
            --space-4: 1.5rem;   /* 24px */
            --space-5: 2rem;     /* 32px */
            --space-6: 3rem;     /* 48px */

            /* Multi-Layered Glassmorphism Tokens */
            --glass-bg-layer-1: linear-gradient(135deg, rgba(15, 23, 42, 0.56) 0%, rgba(15, 23, 42, 0.36) 100%);
            --glass-bg-layer-2: linear-gradient(135deg, rgba(255, 255, 255, 0.11) 0%, rgba(255, 255, 255, 0.04) 100%);
            --glass-bg-layer-3: linear-gradient(135deg, rgba(56, 189, 248, 0.18) 0%, rgba(99, 102, 241, 0.11) 50%, rgba(255, 255, 255, 0.05) 100%);
            --glass-rim: rgba(255, 255, 255, 0.15);
            --glass-rim-top: rgba(255, 255, 255, 0.34);
            --glass-rim-left: rgba(255, 255, 255, 0.24);
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-indigo: #818cf8;
            --accent-emerald: #34d399;
            --accent-amber: #fbbf24;
            --accent-rose: #fb7185;
        }

        /* 1. Vibrant Multi-Orb Mesh Background so Frosted Glass Refracts Real Color */
        .stApp {
            background-color: #050814;
            background-image:
                radial-gradient(circle at 12% 14%, rgba(14, 165, 233, 0.34) 0%, rgba(14, 165, 233, 0.0) 42%),
                radial-gradient(circle at 86% 18%, rgba(124, 58, 237, 0.34) 0%, rgba(124, 58, 237, 0.0) 44%),
                radial-gradient(circle at 78% 78%, rgba(16, 185, 129, 0.24) 0%, rgba(16, 185, 129, 0.0) 45%),
                radial-gradient(circle at 18% 82%, rgba(219, 39, 119, 0.19) 0%, rgba(219, 39, 119, 0.0) 40%),
                linear-gradient(135deg, #050814 0%, #0b132b 48%, #070b19 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Hide noisy Streamlit chrome */
        #MainMenu, footer, [data-testid="stToolbar"] {
            visibility: hidden;
            height: 0;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        .block-container {
            padding-top: var(--space-4) !important;
            padding-bottom: var(--space-6) !important;
            max-width: 1360px !important;
        }

        /* Frosted Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.68) 0%, rgba(9, 13, 28, 0.78) 100%) !important;
            backdrop-filter: blur(24px) saturate(190%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(190%) !important;
            border-right: 1px solid var(--glass-rim) !important;
            box-shadow: 8px 0 32px rgba(2, 6, 23, 0.55);
        }

        /* Layer 1: Base Frosted Glass Panel */
        .glass-layer-1 {
            background: var(--glass-bg-layer-1);
            backdrop-filter: blur(18px) saturate(180%);
            -webkit-backdrop-filter: blur(18px) saturate(180%);
            border: 1px solid var(--glass-rim);
            border-top: 1px solid var(--glass-rim-top);
            border-left: 1px solid var(--glass-rim-left);
            border-radius: 16px;
            padding: var(--space-4);
            box-shadow:
                0 12px 32px -8px rgba(2, 6, 23, 0.55),
                inset 0 1px 0 0 rgba(255, 255, 255, 0.16);
        }

        /* Layer 2: Elevated Interactive Glass Card (Higher Translucency + Stronger Shadow) */
        .glass-layer-2 {
            background: var(--glass-bg-layer-2);
            backdrop-filter: blur(24px) saturate(195%);
            -webkit-backdrop-filter: blur(24px) saturate(195%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-top: 1px solid rgba(255, 255, 255, 0.38);
            border-left: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 16px;
            padding: var(--space-4);
            box-shadow:
                0 20px 44px -10px rgba(2, 6, 23, 0.70),
                inset 0 1px 1px 0 rgba(255, 255, 255, 0.22);
            transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
                        box-shadow 180ms cubic-bezier(0.22, 1, 0.36, 1),
                        border-color 180ms cubic-bezier(0.22, 1, 0.36, 1);
        }

        .glass-layer-2:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.48);
            box-shadow:
                0 26px 54px -10px rgba(2, 6, 23, 0.82),
                0 0 24px rgba(56, 189, 248, 0.16),
                inset 0 1px 1px 0 rgba(255, 255, 255, 0.30);
        }

        /* Layer 3: Spotlight Foreground Glass (Closest to User) */
        .glass-layer-3 {
            background: var(--glass-bg-layer-3);
            backdrop-filter: blur(28px) saturate(210%);
            -webkit-backdrop-filter: blur(28px) saturate(210%);
            border: 1px solid rgba(56, 189, 248, 0.34);
            border-top: 1px solid rgba(255, 255, 255, 0.45);
            border-left: 1px solid rgba(255, 255, 255, 0.32);
            border-radius: 20px;
            padding: var(--space-4);
            box-shadow:
                0 28px 60px -12px rgba(2, 6, 23, 0.85),
                0 0 32px rgba(56, 189, 248, 0.18),
                inset 0 1px 2px 0 rgba(255, 255, 255, 0.28);
        }

        /* Fluid Typography & Tabular Figures (ui-scale-architecture) */
        .hero-title {
            font-size: clamp(1.375rem, 2.2vw, 2rem);
            font-weight: 700;
            letter-spacing: -0.025em;
            line-height: 1.2;
            color: var(--text-primary);
            margin: 0;
        }

        .section-heading {
            font-size: clamp(1.125rem, 1.5vw, 1.35rem);
            font-weight: 700;
            letter-spacing: -0.015em;
            line-height: 1.3;
            color: var(--text-primary);
            margin: 0;
        }

        .spotlight-value {
            font-size: clamp(1.5rem, 2.4vw, 2.25rem);
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.15;
            font-variant-numeric: tabular-nums;
            color: #ffffff;
            margin: 6px 0;
        }

        .spotlight-label {
            font-size: 0.8125rem;
            font-weight: 600;
            color: var(--text-secondary);
            letter-spacing: 0.01em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .spotlight-caption {
            font-size: 0.8125rem;
            color: var(--text-muted);
            line-height: 1.45;
        }

        /* Touch targets & Controls >= 48px (ui-scale-architecture) */
        .stButton > button {
            min-height: 48px !important;
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.88) 0%, rgba(79, 70, 229, 0.88) 100%) !important;
            backdrop-filter: blur(16px) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.28) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.48) !important;
            border-radius: 12px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            font-size: 0.9375rem !important;
            box-shadow: 0 12px 28px -6px rgba(14, 165, 233, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transition: transform 160ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 160ms cubic-bezier(0.22, 1, 0.36, 1) !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 16px 36px -6px rgba(14, 165, 233, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.45) !important;
        }

        .stButton > button:focus-visible {
            outline: 2px solid #38bdf8 !important;
            outline-offset: 2px !important;
        }

        .stDownloadButton > button {
            min-height: 48px !important;
            background: rgba(255, 255, 255, 0.08) !important;
            backdrop-filter: blur(16px) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(255, 255, 255, 0.22) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            min-height: 48px !important;
            background: rgba(15, 23, 42, 0.62) !important;
            backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 12px !important;
            color: #f8fafc !important;
        }

        /* Glass Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(15, 23, 42, 0.48);
            backdrop-filter: blur(16px);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .stTabs [data-baseweb="tab"] {
            min-height: 44px;
            padding: 8px 20px;
            border-radius: 10px;
            color: #cbd5e1;
            font-weight: 600;
            font-size: 0.9375rem;
            border: none !important;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.22) 0%, rgba(99, 102, 241, 0.22) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(56, 189, 248, 0.38) !important;
            box-shadow: 0 4px 14px rgba(14, 165, 233, 0.20);
        }

        /* Metadata Chips with Clear Visual Separation */
        .glass-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 0.8125rem;
            font-weight: 500;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #e2e8f0;
            margin-right: 8px;
            margin-bottom: 6px;
        }

        .highlight-term {
            background: rgba(56, 189, 248, 0.16);
            color: #7dd3fc;
            border: 1px solid rgba(56, 189, 248, 0.32);
            padding: 1px 7px;
            border-radius: 6px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88em;
        }

        @media (prefers-reduced-motion: reduce) {
            *, ::before, ::after {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
    """


def render_red_flag_badge(flag_type: str) -> str:
    """Renders a high-contrast glassmorphic warning pill with custom SVG icon."""
    configs: Dict[str, Dict[str, str]] = {
        "vendor_lockin": {
            "label": "Blokada Vendor Lock-in (.str / EWMAPA)",
            "bg": "rgba(229, 62, 62, 0.20)",
            "border": "rgba(252, 129, 129, 0.45)",
            "color": "#fecaca",
            "icon_color": "#f87171",
            "icon": "shield-alert",
        },
        "asymetria_kar": {
            "label": "Asymetria kar umownych (2% dziennie bez limitu)",
            "bg": "rgba(245, 158, 11, 0.20)",
            "border": "rgba(251, 191, 36, 0.45)",
            "color": "#fde68a",
            "icon_color": "#fbbf24",
            "icon": "scale",
        },
        "krotki_termin": {
            "label": "Nierealny termin realizacji zamówienia",
            "bg": "rgba(139, 92, 246, 0.20)",
            "border": "rgba(196, 181, 253, 0.45)",
            "color": "#ddd6fe",
            "icon_color": "#a78bfa",
            "icon": "layers",
        },
    }

    cfg = configs.get(
        flag_type.lower(),
        {
            "label": f"Ryzyko SWZ: {flag_type}",
            "bg": "rgba(148, 163, 184, 0.18)",
            "border": "rgba(203, 213, 225, 0.35)",
            "color": "#f1f5f9",
            "icon_color": "#cbd5e1",
            "icon": "shield-alert",
        },
    )

    svg = get_svg_icon(cfg["icon"], size=16, color=cfg["icon_color"])
    return _compact_html(f"""
    <span style="display:inline-flex;align-items:center;gap:8px;background-color:{cfg['bg']};color:{cfg['color']};border:1px solid {cfg['border']};border-top:1px solid rgba(255,255,255,0.35);padding:8px 14px;border-radius:999px;font-weight:600;font-size:0.84rem;margin-right:10px;margin-bottom:8px;backdrop-filter:blur(14px);box-shadow:0 6px 18px rgba(2,6,23,0.35);">
        {svg}
        <span>{cfg['label']}</span>
    </span>
    """)


def render_citation_box(citation_text: str) -> str:
    """Renders a concise verified SWZ/OPZ document reference pill."""
    escaped = html.escape(citation_text.strip(" []"))
    svg = get_svg_icon("file-check", size=20, color="#38bdf8")
    return _compact_html(f"""
    <div class="glass-layer-1" style="padding:14px 18px;margin:8px 0;display:flex;align-items:center;gap:12px;border-radius:12px;">
        {svg}
        <div style="font-size:0.9rem;line-height:1.5;color:#f1f5f9;">
            <span style="color:#7dd3fc;font-weight:600;margin-right:6px;">Źródło dowodowe SWZ/OPZ:</span>
            <span style="color:#e2e8f0;font-family:'JetBrains Mono',monospace;font-size:0.85rem;">{escaped}</span>
        </div>
    </div>
    """)


def render_competitor_matrix(competitors: List[Dict[str, str]]) -> str:
    """Renders an HTML glassmorphic table displaying regional GIS competitors."""
    if not competitors:
        return "<div class='glass-layer-1'>Brak zidentyfikowanych podmiotów konkurencyjnych.</div>"

    rows_html = ""
    for comp in competitors:
        name = html.escape(comp.get("name", "Nieznany podmiot"))
        product = html.escape(comp.get("product", "-"))
        advantage = html.escape(comp.get("advantage", "-"))
        rows_html += (
            f"<tr style='border-bottom:1px solid rgba(255,255,255,0.08);'>"
            f"<td style='padding:14px 16px;font-weight:600;color:#f8fafc;'>{name}</td>"
            f"<td style='padding:14px 16px;color:#38bdf8;font-family:\"JetBrains Mono\",monospace;font-size:0.85rem;'>{product}</td>"
            f"<td style='padding:14px 16px;color:#cbd5e1;'>{advantage}</td>"
            f"</tr>"
        )

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:0;overflow:hidden;margin:12px 0;">
        <table style="width:100%;border-collapse:collapse;font-size:0.92rem;text-align:left;">
            <thead>
                <tr style="background:rgba(255,255,255,0.06);color:#94a3b8;border-bottom:1px solid rgba(255,255,255,0.14);font-size:0.78rem;text-transform:uppercase;letter-spacing:0.05em;">
                    <th style="padding:14px 16px;">Podmiot konkurencyjny</th>
                    <th style="padding:14px 16px;">System bazodanowy GIS</th>
                    <th style="padding:14px 16px;">Przewaga w postępowaniu</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """)


def render_kio_warning(risk_level: str) -> str:
    """Renders a high-visibility glass alert indicating KIO appeal grounds."""
    level = risk_level.upper()
    if level == "HIGH":
        bg = "linear-gradient(135deg, rgba(220, 38, 38, 0.22) 0%, rgba(153, 27, 27, 0.12) 100%)"
        border = "rgba(248, 113, 113, 0.45)"
        color = "#fecaca"
        icon_color = "#f87171"
        text = "Ryzyko odwołania do KIO: WYSOKIE (podstawa prawna: art. 16 oraz art. 99 ustawy PZP)"
    elif level == "MEDIUM":
        bg = "linear-gradient(135deg, rgba(217, 119, 6, 0.22) 0%, rgba(146, 64, 14, 0.12) 100%)"
        border = "rgba(251, 191, 36, 0.45)"
        color = "#fde68a"
        icon_color = "#fbbf24"
        text = "Ryzyko odwołania do KIO: ŚREDNIE (zalecane pytanie o równoważność formatów GML/GeoTIFF)"
    else:
        bg = "linear-gradient(135deg, rgba(16, 185, 129, 0.20) 0%, rgba(6, 95, 70, 0.12) 100%)"
        border = "rgba(52, 211, 153, 0.42)"
        color = "#a7f3d0"
        icon_color = "#34d399"
        text = "Ryzyko odwołania do KIO: NISKIE (opis przedmiotu zamówienia dopuszcza standardy otwarte)"

    svg = get_svg_icon("scale", size=24, color=icon_color)
    return _compact_html(f"""
    <div style="background:{bg};color:{color};border:1px solid {border};border-top:1px solid rgba(255,255,255,0.35);padding:16px 20px;border-radius:14px;font-weight:600;font-size:0.95rem;margin:12px 0;display:flex;align-items:center;gap:14px;backdrop-filter:blur(20px);box-shadow:0 14px 32px rgba(2,6,23,0.45);">
        {svg}
        <span>{text}</span>
    </div>
    """)


def format_short_ocds_id(ocds_id: str) -> str:
    """Formats long OCDS UUID identifiers into a clean, readable reference badge."""
    raw = str(ocds_id).strip()
    if len(raw) <= 26:
        return raw
    parts = raw.split("-")
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]}-{parts[2][:8]}"
    return raw[:24]


def render_tender_card(
    ocds_id: str,
    title: str,
    municipality: str,
    voivodeship: str,
    budget_pln: float,
    status: str = "ACTIVE",
    is_selected: bool = False,
) -> str:
    """Renders a multi-layered glassmorphic tender card with clear chip separation."""
    safe_title = html.escape(str(title))
    safe_muni = html.escape(str(municipality))
    safe_voiv = html.escape(str(voivodeship))
    safe_full_id = html.escape(str(ocds_id))
    short_id = html.escape(format_short_ocds_id(ocds_id))
    status_pl = "Aktywne" if str(status).upper() == "ACTIVE" else html.escape(str(status))

    if budget_pln and budget_pln > 0:
        budget_str = f"{budget_pln:,.0f} PLN".replace(",", " ")
        budget_color = "#34d399"
    else:
        budget_str = "Wg kosztorysu SWZ"
        budget_color = "#94a3b8"

    building_svg = get_svg_icon("building", size=16, color="#38bdf8")
    pin_svg = get_svg_icon("map-pin", size=16, color="#818cf8")
    wallet_svg = get_svg_icon("wallet", size=16, color=budget_color)

    layer_class = "glass-layer-3" if is_selected else "glass-layer-2"
    selected_badge = (
        '<span style="background:rgba(56,189,248,0.22);color:#7dd3fc;border:1px solid rgba(56,189,248,0.45);'
        'padding:4px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;">Wybrane do analizy</span>'
        if is_selected
        else f'<span style="background:rgba(16,185,129,0.16);color:#6ee7b7;border:1px solid rgba(52,211,153,0.35);padding:4px 10px;border-radius:999px;font-size:0.75rem;font-weight:600;">{status_pl}</span>'
    )

    return _compact_html(f"""
    <div class="{layer_class}" style="margin-bottom:16px;" data-ocds-id="{safe_full_id}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px;">
            <div style="font-size:1.05rem;font-weight:700;color:#f8fafc;line-height:1.4;">{safe_title}</div>
            {selected_badge}
        </div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;">
            <span class="glass-chip" title="{safe_full_id}" style="font-family:'JetBrains Mono',monospace;color:#7dd3fc;">
                Ref: {short_id}
            </span>
            <span class="glass-chip">
                {building_svg}
                <span>Zamawiający: <strong style="color:#f8fafc;">{safe_muni}</strong></span>
            </span>
            <span class="glass-chip">
                {pin_svg}
                <span>Województwo: <strong style="color:#f8fafc;">{safe_voiv}</strong></span>
            </span>
            <span class="glass-chip" style="border-color:rgba(52,211,153,0.28);">
                {wallet_svg}
                <span>Budżet: <strong style="color:{budget_color};font-variant-numeric:tabular-nums;">{budget_str}</strong></span>
            </span>
        </div>
    </div>
    """)


def highlight_domain_terms(text: str) -> str:
    """Highlights critical GIS & PZP legal/technical terms inside an escaped HTML snippet."""
    escaped = html.escape(text)
    escaped = re.sub(r"\[([^\[\]]+)\]", r'<span class="highlight-term">[\1]</span>', escaped)
    keywords = [
        r"\.str",
        r"EWMAPA",
        r"BDOT500",
        r"GESUT",
        r"EGiB",
        r"OŚRODEK",
        r"OSRODEK",
        r"iMPA",
        r"Vendor Lock-in",
        r"art\.\s*16",
        r"art\.\s*99",
        r"PZP",
        r"KIO",
        r"320\s*000,00\s*PLN",
        r"2%",
    ]
    for kw in keywords:
        escaped = re.sub(
            rf"({kw})",
            r'<strong style="color:#7dd3fc;font-weight:700;">\1</strong>',
            escaped,
            flags=re.IGNORECASE,
        )
    return escaped


def render_insight_section_card(title: str, body: str, icon_name: str, accent_color: str = "#38bdf8") -> str:
    """Renders a single structured audit section as an elevated frosted-glass card."""
    svg = get_svg_icon(icon_name, size=24, color=accent_color)
    formatted_body = highlight_domain_terms(body.strip()) if body.strip() else "Brak dodatkowych uwag w tej sekcji."
    return _compact_html(f"""
    <div class="glass-layer-2" style="height:100%;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,0.10);">
            <div style="width:40px;height:40px;border-radius:10px;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.16);display:flex;align-items:center;justify-content:center;">
                {svg}
            </div>
            <h3 style="margin:0;font-size:1.05rem;font-weight:700;color:#f8fafc;letter-spacing:-0.01em;">{html.escape(title)}</h3>
        </div>
        <div style="font-size:0.95rem;line-height:1.65;color:#e2e8f0;max-width:72ch;">
            {formatted_body}
        </div>
    </div>
    """)
