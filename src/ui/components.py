import html
import re
from typing import Any, Dict, List


def _compact_html(raw_html: str) -> str:
    """Removes line-leading indentation so Streamlit's CommonMark parser never treats HTML as a code block."""
    return "\n".join(line.strip() for line in raw_html.strip().splitlines() if line.strip())


def get_svg_icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    """Returns clean, custom inline SVG vector icons sized strictly on the 8pt/4pt UI scale (16, 20, 24, 32, 48)."""
    allowed_sizes = {16, 20, 24, 32, 48}
    resolved_size = size if size in allowed_sizes else 20
    icons: Dict[str, str] = {
        "brand-mark": (
            '<path d="M12 3 4 9l8 6 8-6-8-6Z" fill="rgba(37,99,235,0.18)"></path>'
            '<path d="M4 14l8 6 8-6"></path>'
            '<path d="M12 3 4 9l8 6 8-6-8-6Z"></path>'
        ),
        "home": (
            '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>'
            '<polyline points="9 22 9 12 15 12 15 22"></polyline>'
        ),
        "search": (
            '<circle cx="11" cy="11" r="8"></circle>'
            '<line x1="21" y1="21" x2="16.65" y2="16.65"></line>'
        ),
        "bell": (
            '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>'
            '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>'
        ),
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
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;vertical-align:middle;display:inline-block;">{body}</svg>'
    )


def get_glassmorphism_stylesheet() -> str:
    """Returns a bright, airy Daylight Frosted-Glass SaaS stylesheet with purposeful state transitions."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg-canvas: #f3f6fb;
            --surface-white: rgba(255, 255, 255, 0.88);
            --surface-elevated: rgba(255, 255, 255, 0.96);
            --surface-spotlight: rgba(255, 255, 255, 0.98);
            --border-subtle: rgba(226, 232, 240, 0.95);
            --border-focus: #2563eb;
            --ink-primary: #0f172a;
            --ink-secondary: #475569;
            --ink-muted: #64748b;
            --brand-blue: #2563eb;
            --brand-coral: #ff6b57;
            --brand-amber: #f59e0b;
            --brand-emerald: #10b981;
            --ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);
            --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
        }

        /* Animations */
        @keyframes cardSlideUp {
            from {
                opacity: 0;
                transform: translateY(12px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes barGrowVertical {
            from {
                transform: scaleY(0.08);
            }
            to {
                transform: scaleY(1);
            }
        }

        @keyframes statusDotPulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.45);
            }
            50% {
                box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.0);
            }
        }

        /* App Canvas */
        .stApp {
            background-color: var(--bg-canvas) !important;
            background-image:
                radial-gradient(at 15% 8%, rgba(59, 130, 246, 0.07) 0px, transparent 45%),
                radial-gradient(at 88% 12%, rgba(16, 185, 129, 0.06) 0px, transparent 42%),
                radial-gradient(at 50% 90%, rgba(99, 102, 241, 0.05) 0px, transparent 50%) !important;
            color: var(--ink-primary) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        #MainMenu, footer, [data-testid="stToolbar"] {
            visibility: hidden;
            height: 0;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 2rem !important;
        }

        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 3rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1440px !important;
        }

        /* Crisp White Sidebar */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid #e8eef5 !important;
            box-shadow: 4px 0 24px rgba(15, 23, 42, 0.03) !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem !important;
        }

        /* Glass & Card Surfaces (Daylight Frosted) */
        .glass-layer-1 {
            background: var(--surface-white);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
            animation: cardSlideUp 320ms var(--ease-out-quint) both;
        }

        .glass-layer-2 {
            background: var(--surface-elevated);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 22px 24px;
            box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
            transition: transform 200ms var(--ease-out-quint),
                        box-shadow 200ms var(--ease-out-quint),
                        border-color 200ms var(--ease-out-quint);
            animation: cardSlideUp 360ms var(--ease-out-quint) both;
        }

        .glass-layer-2:hover {
            transform: translateY(-3px);
            border-color: #cbd5e1;
            box-shadow: 0 12px 28px -4px rgba(15, 23, 42, 0.08), 0 4px 10px -2px rgba(37, 99, 235, 0.05);
        }

        .glass-layer-3 {
            background: var(--surface-spotlight);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(37, 99, 235, 0.28);
            border-radius: 16px;
            padding: 22px 24px;
            box-shadow: 0 10px 30px -4px rgba(37, 99, 235, 0.10), 0 4px 12px rgba(15, 23, 42, 0.04);
            transition: transform 200ms var(--ease-out-quint), box-shadow 200ms var(--ease-out-quint);
            animation: cardSlideUp 380ms var(--ease-out-quint) both;
        }

        /* Form Controls & Selectboxes */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            min-height: 44px !important;
            background-color: #ffffff !important;
            border: 1px solid #dbe3ee !important;
            border-radius: 10px !important;
            color: #0f172a !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
            transition: border-color 160ms var(--ease-out-quart), box-shadow 160ms var(--ease-out-quart) !important;
        }

        div[data-baseweb="select"] > div:hover,
        div[data-baseweb="input"] > div:hover {
            border-color: #94a3b8 !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="input"] > div:focus-within {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
        }

        .stSelectbox label, .stTextInput label, .stNumberInput label {
            color: #334155 !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            margin-bottom: 4px !important;
        }

        /* Clean Primary Action Button (Matches the clean blue button in the inspiration UI) */
        .stButton > button {
            min-height: 44px !important;
            background: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
            border-radius: 10px !important;
            padding: 0.5rem 1.25rem !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22) !important;
            transition: transform 150ms var(--ease-out-quint),
                        background-color 150ms var(--ease-out-quint),
                        box-shadow 150ms var(--ease-out-quint) !important;
        }

        .stButton > button:hover {
            background: #1d4ed8 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.30) !important;
        }

        .stButton > button:active {
            transform: scale(0.98) !important;
        }

        .stDownloadButton > button {
            min-height: 42px !important;
            background: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
            transition: all 150ms var(--ease-out-quart) !important;
        }

        .stDownloadButton > button:hover {
            background: #f8fafc !important;
            border-color: #2563eb !important;
            color: #2563eb !important;
        }

        /* Pill Tabs (Matches the clean green/white pill tabs in the inspiration image) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background: #ffffff;
            padding: 5px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
        }

        .stTabs [data-baseweb="tab"] {
            min-height: 38px;
            padding: 6px 16px;
            border-radius: 8px;
            color: #64748b !important;
            font-weight: 600;
            font-size: 0.84rem;
            border: none !important;
            transition: all 180ms var(--ease-out-quart);
        }

        .stTabs [aria-selected="true"] {
            background: #10b981 !important;
            color: #ffffff !important;
            box-shadow: 0 3px 10px rgba(16, 185, 129, 0.25);
        }

        .stTabs [data-baseweb="tab-panel"] {
            animation: cardSlideUp 260ms var(--ease-out-quint) both;
            padding-top: 16px !important;
        }

        /* Chips & Domain Highlights */
        .glass-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 11px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            color: #334155;
            margin-right: 6px;
            margin-bottom: 4px;
        }

        .highlight-term {
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
            padding: 1px 6px;
            border-radius: 5px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.86em;
        }

        /* Animated vertical chart bars */
        .v-bar-fill {
            transform-origin: bottom;
            animation: barGrowVertical 650ms var(--ease-out-quint) both;
        }

        @media (prefers-reduced-motion: reduce) {
            *, ::before, ::after {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
    """


def render_brand_sidebar_header() -> str:
    """Renders the compact geometric logo and app title in the top-left of the sidebar."""
    logo_svg = get_svg_icon("brand-mark", size=24, color="#2563eb")
    return _compact_html(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:4px 4px 20px 4px;border-bottom:1px solid #f1f5f9;margin-bottom:18px;">
        <div style="width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);border:1px solid #bfdbfe;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(37,99,235,0.12);">
            {logo_svg}
        </div>
        <div>
            <div style="font-size:1.02rem;font-weight:800;color:#0f172a;letter-spacing:-0.02em;line-height:1.15;">GisMarket</div>
            <div style="font-size:0.74rem;font-weight:600;color:#64748b;letter-spacing:0.01em;">Intelligence AI</div>
        </div>
    </div>
    """)


def render_top_utility_bar(
    municipality: str,
    voivodeship: str,
    ollama_ok: bool,
    total_tenders: int,
    has_lockin: bool,
) -> str:
    """Renders a clean top navbar with breadcrumbs on the left and status pills on the right."""
    home_svg = get_svg_icon("home", size=16, color="#2563eb")
    bell_svg = get_svg_icon("bell", size=16, color="#f59e0b" if has_lockin else "#10b981")
    safe_muni = html.escape(municipality)
    safe_voiv = html.escape(voivodeship)

    alert_text = (
        'Wykryto <strong style="color:#dc2626;">2 ryzyka KIO</strong> w SWZ'
        if has_lockin
        else 'Dokumentacja <strong style="color:#10b981;">zgodna z PZP</strong>'
    )
    dot_color = "#10b981" if ollama_ok else "#f59e0b"
    env_label = "Ollama AI + pgvector" if ollama_ok else "Tryb deterministyczny + pgvector"

    return _compact_html(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:20px;padding:6px 2px;">
        <div style="display:flex;align-items:center;gap:8px;font-size:0.86rem;color:#64748b;font-weight:500;">
            {home_svg}
            <span>Panel główny</span>
            <span style="color:#cbd5e1;">&rsaquo;</span>
            <span>Audyt zamówień GIS</span>
            <span style="color:#cbd5e1;">&rsaquo;</span>
            <span style="color:#0f172a;font-weight:700;">{safe_muni} ({safe_voiv})</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <div style="display:inline-flex;align-items:center;gap:8px;background:#ffffff;border:1px solid #e2e8f0;padding:7px 14px;border-radius:999px;font-size:0.8rem;color:#334155;box-shadow:0 2px 6px rgba(15,23,42,0.03);">
                <span>{alert_text}</span>
                {bell_svg}
            </div>
            <div style="display:inline-flex;align-items:center;gap:8px;background:#ffffff;border:1px solid #e2e8f0;padding:7px 14px;border-radius:999px;font-size:0.8rem;color:#0f172a;font-weight:600;box-shadow:0 2px 6px rgba(15,23,42,0.03);">
                <span style="width:8px;height:8px;border-radius:50%;background:{dot_color};animation:statusDotPulse 2.4s infinite;display:inline-block;"></span>
                <span>{env_label}</span>
                <span style="background:#eff6ff;color:#2563eb;padding:1px 7px;border-radius:999px;font-size:0.72rem;font-weight:700;">{total_tenders} SWZ</span>
            </div>
        </div>
    </div>
    """)


def render_kpi_stat_card(
    value: str,
    label: str,
    sublabel: str,
    icon_name: str,
    color_hex: str,
    ring_bg: str,
    stagger_index: int = 0,
) -> str:
    """Renders a clean horizontal KPI card with a circular colored icon badge (inspired by modern SaaS dashboards)."""
    svg = get_svg_icon(icon_name, size=24, color="#ffffff")
    delay_ms = stagger_index * 55
    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:20px 22px;display:flex;align-items:center;gap:18px;animation-delay:{delay_ms}ms;">
        <div style="width:54px;height:54px;border-radius:50%;background:{color_hex};box-shadow:0 0 0 6px {ring_bg}, 0 6px 16px {ring_bg};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            {svg}
        </div>
        <div style="min-width:0;">
            <div style="font-size:1.55rem;font-weight:800;color:{color_hex};line-height:1.15;letter-spacing:-0.025em;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {html.escape(value)}
            </div>
            <div style="font-size:0.84rem;font-weight:700;color:#1e293b;margin-top:3px;">
                {html.escape(label)}
            </div>
            <div style="font-size:0.74rem;color:#64748b;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {html.escape(sublabel)}
            </div>
        </div>
    </div>
    """)


def render_risk_profile_panel(has_lockin: bool, has_penalties: bool, faithfulness: float) -> str:
    """Renders the right-hand vertical bar chart card with an overall score summary at the bottom."""
    b1 = 92 if has_lockin else 22
    b2 = 86 if has_penalties else 28
    b3 = 64
    b4 = int(round(faithfulness * 100))
    overall_score = int(round((b1 + b2 + b3) / 3))

    bars = [
        ("Format", b1, "#3b82f6"),
        ("Kary", b2, "#6366f1"),
        ("Kadra", b3, "#8b5cf6"),
        ("RAGAS", b4, "#10b981"),
    ]
    bars_html = ""
    for idx, (lbl, pct, col) in enumerate(bars):
        delay = idx * 80
        bars_html += (
            f"<div style='display:flex;flex-direction:column;align-items:center;gap:8px;flex:1;'>"
            f"<div style='height:150px;width:28px;background:#f1f5f9;border-radius:8px;display:flex;align-items:flex-end;overflow:hidden;padding:2px;'>"
            f"<div class='v-bar-fill' style='width:100%;height:{pct}%;background:{col};border-radius:6px;animation-delay:{delay}ms;'></div>"
            f"</div>"
            f"<span style='font-size:0.75rem;font-weight:600;color:#64748b;'>{lbl}</span>"
            f"<span style='font-size:0.72rem;font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums;'>{pct}%</span>"
            f"</div>"
        )

    verdict_note = (
        "Wysoki poziom restrykcyjności SWZ (wymagany wniosek z art. 135 PZP)"
        if has_lockin
        else "Standardowy profil wymagań przetargowych"
    )

    return _compact_html(f"""
    <div class="glass-layer-2" style="height:100%;display:flex;flex-direction:column;justify-content:space-between;">
        <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
                <span style="font-size:1.02rem;font-weight:800;color:#0f172a;">Profil ryzyka SWZ</span>
                <span style="font-size:0.74rem;font-weight:700;color:#2563eb;background:#eff6ff;padding:4px 10px;border-radius:999px;">Indeks barier</span>
            </div>
            <div style="display:flex;justify-content:space-around;align-items:flex-end;gap:12px;padding:14px 8px 18px 8px;border-bottom:1px solid #f1f5f9;">
                {bars_html}
            </div>
        </div>
        <div style="text-align:center;padding-top:18px;">
            <div style="font-size:2.1rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;line-height:1.1;font-variant-numeric:tabular-nums;">
                {overall_score} <span style="font-size:1rem;font-weight:600;color:#94a3b8;">/ 100</span>
            </div>
            <div style="font-size:0.8rem;color:#64748b;margin-top:6px;line-height:1.4;">
                {verdict_note}
            </div>
            <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:14px;">
                <span class="glass-chip" style="background:#fff1f2;color:#e11d48;border-color:#fecdd3;">Geobid: EWMAPA (.str)</span>
                <span class="glass-chip" style="background:#eff6ff;color:#2563eb;border-color:#bfdbfe;">Geo-System: iMPA</span>
            </div>
        </div>
    </div>
    """)


def render_red_flag_badge(flag_type: str) -> str:
    """Renders a crisp semantic warning pill with custom SVG icon."""
    configs: Dict[str, Dict[str, str]] = {
        "vendor_lockin": {
            "label": "Vendor Lock-in (.str / EWMAPA)",
            "bg": "#fff1f2",
            "border": "#fecdd3",
            "color": "#be123c",
            "icon_color": "#e11d48",
            "icon": "shield-alert",
        },
        "asymetria_kar": {
            "label": "Asymetria kar umownych (2% dziennie bez limitu)",
            "bg": "#fffbeb",
            "border": "#fde68a",
            "color": "#b45309",
            "icon_color": "#d97706",
            "icon": "scale",
        },
        "krotki_termin": {
            "label": "Krótki termin realizacji zamówienia",
            "bg": "#f5f3ff",
            "border": "#ddd6fe",
            "color": "#6d28d9",
            "icon_color": "#7c3aed",
            "icon": "layers",
        },
    }

    cfg = configs.get(
        flag_type.lower(),
        {
            "label": f"Ryzyko SWZ: {flag_type}",
            "bg": "#f1f5f9",
            "border": "#cbd5e1",
            "color": "#334155",
            "icon_color": "#475569",
            "icon": "shield-alert",
        },
    )

    svg = get_svg_icon(cfg["icon"], size=16, color=cfg["icon_color"])
    return _compact_html(f"""
    <span style="display:inline-flex;align-items:center;gap:7px;background-color:{cfg['bg']};color:{cfg['color']};border:1px solid {cfg['border']};padding:6px 13px;border-radius:999px;font-weight:600;font-size:0.8rem;margin-right:8px;margin-bottom:6px;">
        {svg}
        <span>{cfg['label']}</span>
    </span>
    """)


def render_citation_box(citation_text: str) -> str:
    """Renders a concise verified SWZ/OPZ document reference pill."""
    escaped = html.escape(citation_text.strip(" []"))
    svg = get_svg_icon("file-check", size=20, color="#2563eb")
    return _compact_html(f"""
    <div class="glass-layer-1" style="padding:12px 16px;margin:8px 0;display:flex;align-items:center;gap:12px;border-radius:12px;">
        {svg}
        <div style="font-size:0.86rem;line-height:1.45;color:#1e293b;">
            <span style="color:#2563eb;font-weight:700;margin-right:6px;">Źródło dowodowe SWZ/OPZ:</span>
            <span style="color:#334155;font-family:'JetBrains Mono',monospace;font-size:0.82rem;">{escaped}</span>
        </div>
    </div>
    """)


def render_competitor_matrix(competitors: List[Dict[str, str]]) -> str:
    """Renders a clean light-mode table displaying regional GIS competitors."""
    if not competitors:
        return "<div class='glass-layer-1'>Brak zidentyfikowanych podmiotów konkurencyjnych.</div>"

    rows_html = ""
    for comp in competitors:
        name = html.escape(comp.get("name", "Nieznany podmiot"))
        product = html.escape(comp.get("product", "-"))
        advantage = html.escape(comp.get("advantage", "-"))
        rows_html += (
            f"<tr style='border-bottom:1px solid #f1f5f9;'>"
            f"<td style='padding:13px 16px;font-weight:700;color:#0f172a;'>{name}</td>"
            f"<td style='padding:13px 16px;'><span style='background:#eff6ff;color:#2563eb;padding:3px 9px;border-radius:6px;font-family:\"JetBrains Mono\",monospace;font-size:0.8rem;font-weight:600;'>{product}</span></td>"
            f"<td style='padding:13px 16px;color:#475569;'>{advantage}</td>"
            f"</tr>"
        )

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:0;overflow:hidden;margin:8px 0;">
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem;text-align:left;">
            <thead>
                <tr style="background:#f8fafc;color:#64748b;border-bottom:1px solid #e2e8f0;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;">
                    <th style="padding:12px 16px;">Podmiot konkurencyjny</th>
                    <th style="padding:12px 16px;">System bazodanowy GIS</th>
                    <th style="padding:12px 16px;">Przewaga w postępowaniu</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """)


def render_kio_warning(risk_level: str) -> str:
    """Renders a clean semantic alert indicating KIO appeal grounds."""
    level = risk_level.upper()
    if level == "HIGH":
        bg = "#fff1f2"
        border = "#fecdd3"
        color = "#9f1239"
        icon_color = "#e11d48"
        text = "Ryzyko odwołania do KIO: WYSOKIE (podstawa prawna: art. 16 oraz art. 99 ustawy PZP)"
    elif level == "MEDIUM":
        bg = "#fffbeb"
        border = "#fde68a"
        color = "#92400e"
        icon_color = "#d97706"
        text = "Ryzyko odwołania do KIO: ŚREDNIE (zalecane pytanie o równoważność formatów GML/GeoTIFF)"
    else:
        bg = "#ecfdf5"
        border = "#a7f3d0"
        color = "#065f46"
        icon_color = "#10b981"
        text = "Ryzyko odwołania do KIO: NISKIE (opis przedmiotu zamówienia dopuszcza standardy otwarte)"

    svg = get_svg_icon("scale", size=20, color=icon_color)
    return _compact_html(f"""
    <div style="background:{bg};color:{color};border:1px solid {border};padding:12px 16px;border-radius:12px;font-weight:600;font-size:0.88rem;margin:8px 0 14px 0;display:flex;align-items:center;gap:12px;">
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
    """Renders a clean daylight card with metadata chips."""
    safe_title = html.escape(str(title))
    safe_muni = html.escape(str(municipality))
    safe_voiv = html.escape(str(voivodeship))
    safe_full_id = html.escape(str(ocds_id))
    short_id = html.escape(format_short_ocds_id(ocds_id))
    status_pl = "Aktywne" if str(status).upper() == "ACTIVE" else html.escape(str(status))

    if budget_pln and budget_pln > 0:
        budget_str = f"{budget_pln:,.0f} PLN".replace(",", " ")
        budget_color = "#059669"
    else:
        budget_str = "Wg kosztorysu SWZ"
        budget_color = "#64748b"

    building_svg = get_svg_icon("building", size=16, color="#2563eb")
    pin_svg = get_svg_icon("map-pin", size=16, color="#6366f1")
    wallet_svg = get_svg_icon("wallet", size=16, color=budget_color)

    layer_class = "glass-layer-3" if is_selected else "glass-layer-2"
    selected_badge = (
        '<span style="background:#2563eb;color:#ffffff;padding:4px 11px;border-radius:999px;font-size:0.74rem;font-weight:700;">W analizie</span>'
        if is_selected
        else f'<span style="background:#10b981;color:#ffffff;padding:4px 11px;border-radius:999px;font-size:0.74rem;font-weight:600;">{status_pl}</span>'
    )

    return _compact_html(f"""
    <div class="{layer_class}" style="margin-bottom:12px;padding:16px 20px;" data-ocds-id="{safe_full_id}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:10px;">
            <div style="font-size:0.96rem;font-weight:700;color:#0f172a;line-height:1.4;">{safe_title}</div>
            {selected_badge}
        </div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;">
            <span class="glass-chip" title="{safe_full_id}" style="font-family:'JetBrains Mono',monospace;color:#2563eb;background:#eff6ff;border-color:#bfdbfe;">
                {short_id}
            </span>
            <span class="glass-chip">
                {building_svg}
                <span>Zamawiający: <strong style="color:#0f172a;">{safe_muni}</strong></span>
            </span>
            <span class="glass-chip">
                {pin_svg}
                <span>Województwo: <strong style="color:#0f172a;">{safe_voiv}</strong></span>
            </span>
            <span class="glass-chip">
                {wallet_svg}
                <span>Budżet: <strong style="color:{budget_color};font-variant-numeric:tabular-nums;">{budget_str}</strong></span>
            </span>
        </div>
    </div>
    """)


def render_procurements_table(rows: List[Dict[str, Any]], selected_id: str) -> str:
    """Renders a modern SaaS table card (inspired by the Orders table in the reference dashboard)."""
    check_svg = get_svg_icon("check-circle", size=16, color="#10b981")
    building_svg = get_svg_icon("building", size=16, color="#2563eb")

    tbody = ""
    for row in rows:
        row_id = str(row.get("ID", ""))
        short_id = html.escape(format_short_ocds_id(row_id))
        muni = html.escape(str(row.get("Zamawiający", "")))
        title = html.escape(str(row.get("Tytuł", "")))
        voiv = html.escape(str(row.get("Województwo", "")))
        budget_val = float(row.get("Budżet PLN", 0.0) or 0.0)
        budget_str = f"{budget_val:,.0f} PLN".replace(",", " ") if budget_val > 0 else "Wg SWZ"

        is_sel = row_id == selected_id
        row_bg = "background:#f8fafc;" if is_sel else ""
        status_pill = (
            "<span style='background:#2563eb;color:#ffffff;padding:4px 12px;border-radius:6px;font-size:0.74rem;font-weight:700;display:inline-block;'>W analizie</span>"
            if is_sel
            else "<span style='background:#10b981;color:#ffffff;padding:4px 12px;border-radius:6px;font-size:0.74rem;font-weight:700;display:inline-block;'>Aktywne</span>"
        )

        tbody += (
            f"<tr style='border-bottom:1px solid #f1f5f9;{row_bg}transition:background 150ms ease;'>"
            f"<td style='padding:14px 16px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<div style='width:34px;height:34px;border-radius:50%;background:#eff6ff;display:flex;align-items:center;justify-content:center;flex-shrink:0;'>{building_svg}</div>"
            f"<span style='font-weight:700;color:#0f172a;font-size:0.86rem;'>{muni}</span>"
            f"</div>"
            f"</td>"
            f"<td style='padding:14px 16px;color:#334155;font-size:0.85rem;font-weight:500;max-width:420px;'>{title}</td>"
            f"<td style='padding:14px 16px;font-family:\"JetBrains Mono\",monospace;font-size:0.78rem;color:#64748b;'>{short_id}</td>"
            f"<td style='padding:14px 16px;color:#475569;font-size:0.84rem;'>{voiv}</td>"
            f"<td style='padding:14px 16px;font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums;font-size:0.86rem;'>{budget_str}</td>"
            f"<td style='padding:14px 16px;'>"
            f"<span style='display:inline-flex;align-items:center;gap:6px;color:#10b981;font-weight:600;font-size:0.8rem;'>{check_svg}<span>Zindeksowano</span></span>"
            f"</td>"
            f"<td style='padding:14px 16px;text-align:right;'>{status_pill}</td>"
            f"</tr>"
        )

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:22px 24px;margin-top:20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <h3 style="margin:0;font-size:1.08rem;font-weight:800;color:#0f172a;">Postępowania przetargowe w bazie</h3>
                <div style="font-size:0.8rem;color:#64748b;margin-top:2px;">Zestawienie ogłoszeń BZP oraz zindeksowanych specyfikacji SWZ/OPZ</div>
            </div>
            <span style="font-size:0.78rem;font-weight:700;color:#2563eb;background:#eff6ff;padding:5px 12px;border-radius:999px;">Łącznie: {len(rows)}</span>
        </div>
        <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;text-align:left;">
                <thead>
                    <tr style="border-bottom:1px solid #e2e8f0;color:#64748b;font-size:0.76rem;font-weight:700;text-transform:uppercase;letter-spacing:0.03em;">
                        <th style="padding:10px 16px;">Zamawiający</th>
                        <th style="padding:10px 16px;">Przedmiot zamówienia</th>
                        <th style="padding:10px 16px;">Nr ref.</th>
                        <th style="padding:10px 16px;">Województwo</th>
                        <th style="padding:10px 16px;">Szacunek</th>
                        <th style="padding:10px 16px;">Status RAG</th>
                        <th style="padding:10px 16px;text-align:right;">Etap</th>
                    </tr>
                </thead>
                <tbody>{tbody}</tbody>
            </table>
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
            r'<strong style="color:#2563eb;font-weight:700;">\1</strong>',
            escaped,
            flags=re.IGNORECASE,
        )
    return escaped


def render_insight_section_card(title: str, body: str, icon_name: str, accent_color: str = "#2563eb") -> str:
    """Renders a single structured audit section as a crisp light-mode card."""
    svg = get_svg_icon(icon_name, size=20, color=accent_color)
    formatted_body = highlight_domain_terms(body.strip()) if body.strip() else "Brak dodatkowych uwag w tej sekcji."
    return _compact_html(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin-bottom:12px;height:100%;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="width:32px;height:32px;border-radius:8px;background:#ffffff;border:1px solid #e2e8f0;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(15,23,42,0.04);">
                {svg}
            </div>
            <h4 style="margin:0;font-size:0.92rem;font-weight:700;color:#0f172a;">{html.escape(title)}</h4>
        </div>
        <div style="font-size:0.86rem;line-height:1.6;color:#334155;max-width:72ch;">
            {formatted_body}
        </div>
    </div>
    """)


def render_direct_answer_card(question: str, answer: str) -> str:
    """Renders a spotlight card with the direct RAG answer to the user's question."""
    sparkles_svg = get_svg_icon("sparkles", size=20, color="#2563eb")
    safe_q = html.escape(question.strip())
    formatted_ans = highlight_domain_terms(answer.strip())
    return _compact_html(f"""
    <div style="background:linear-gradient(135deg,#eff6ff 0%,#f8fafc 100%);border:1px solid #bfdbfe;border-radius:14px;padding:16px 20px;margin:8px 0 16px 0;box-shadow:0 4px 14px rgba(37,99,235,0.06);">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="width:34px;height:34px;border-radius:9px;background:#ffffff;border:1px solid #bfdbfe;display:flex;align-items:center;justify-content:center;">
                {sparkles_svg}
            </div>
            <div>
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#2563eb;font-weight:800;">
                    Bezpośrednia odpowiedź asystenta RAG
                </div>
                <div style="font-size:0.9rem;font-weight:700;color:#0f172a;">
                    Pytanie: {safe_q}
                </div>
            </div>
        </div>
        <div style="font-size:0.9rem;line-height:1.6;color:#1e293b;padding-left:44px;">
            {formatted_ans}
        </div>
    </div>
    """)
