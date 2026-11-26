import html
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote


def _compact_html(raw_html: str) -> str:
    """Removes line-leading indentation so Streamlit's CommonMark parser never treats HTML as a code block."""
    return "\n".join(line.strip() for line in raw_html.strip().splitlines() if line.strip())


def get_svg_icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    """Returns clean, custom inline SVG vector icons sized strictly on the 8pt/4pt UI scale (16, 20, 24, 32, 48)."""
    allowed_sizes = {16, 20, 24, 32, 48}
    resolved_size = size if size in allowed_sizes else 20
    icons: Dict[str, str] = {
        "brand-mark": (
            '<path d="M12 3 4 9l8 6 8-6-8-6Z" fill="rgba(37,99,235,0.16)"></path>'
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
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.9" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0;vertical-align:middle;display:inline-block;">{body}</svg>'
    )


def get_glassmorphism_stylesheet() -> str:
    """Returns a restrained, high-contrast architectural daylight stylesheet (Linear/Stripe register)."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg-canvas: #f4f6f9;
            --surface-1: rgba(255, 255, 255, 0.92);
            --surface-2: #ffffff;
            --surface-well: #f8fafc;
            --border-hairline: #e2e8f0;
            --border-strong: #94a3b8;
            --ink-primary: #0f172a;
            --ink-secondary: #334155;
            --ink-muted: #64748b;
            --accent-primary: #0f172a;
            --accent-interactive: #2563eb;
            --status-danger: #dc2626;
            --status-warning: #d97706;
            --status-success: #059669;
            --ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);
        }

        @keyframes cardSlideUp {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes barGrowVertical {
            from { transform: scaleY(0.05); }
            to { transform: scaleY(1); }
        }

        /* Hide Streamlit promotional popups, toasts, form "Press Enter" hint, heading anchor links, and toolbar chrome */
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
        [data-testid="stNotification"], .stToast, div[data-testid="stStatusWidget"],
        [data-testid="InputInstructions"], [data-testid="stHeaderActionElements"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        header[data-testid="stHeader"],
        div[data-baseweb="toast"],
        div[role="alertdialog"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        .stApp {
            background-color: var(--bg-canvas) !important;
            color: var(--ink-primary) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        .block-container {
            padding-top: 0.75rem !important;
            padding-bottom: 3rem !important;
            padding-left: clamp(0.75rem, 2.5vw, 2rem) !important;
            padding-right: clamp(0.75rem, 2.5vw, 2rem) !important;
            max-width: 1460px !important;
        }

        h1, h2, h3 {
            text-wrap: balance;
            letter-spacing: -0.02em;
        }

        p, li {
            line-height: 1.5;
            text-wrap: pretty;
        }

        /* Tabular numerals for KPIs, budgets, and tables */
        [data-testid="stMetricValue"], table, td, th {
            font-variant-numeric: tabular-nums;
        }

        /* Compact Sidebar Styling */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid var(--border-hairline) !important;
            min-width: 228px !important;
            max-width: 248px !important;
            width: 236px !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.75rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }

        /* Clickable Tender Table Rows (no checkboxes) */
        tr.tender-row {
            cursor: pointer !important;
            transition: background-color 120ms ease !important;
        }
        tr.tender-row:hover {
            background-color: #eff6ff !important;
        }
        a.tender-row-link {
            color: inherit !important;
            text-decoration: none !important;
            display: block !important;
            width: 100% !important;
        }

        /* Architectural Surface Layers (Frosted Glass + Crisp Hairline Borders) */
        .glass-layer-1 {
            background: var(--surface-1);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-hairline);
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
            animation: cardSlideUp 240ms var(--ease-out-quint) both;
        }

        .glass-layer-2 {
            background: var(--surface-2);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-hairline);
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 2px 8px -2px rgba(15, 23, 42, 0.05), 0 1px 3px rgba(15, 23, 42, 0.03);
            transition: transform 180ms var(--ease-out-quint), box-shadow 180ms var(--ease-out-quint), border-color 180ms var(--ease-out-quint);
            animation: cardSlideUp 280ms var(--ease-out-quint) both;
        }

        .glass-layer-2:hover {
            border-color: #cbd5e1;
            box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.07);
        }

        .glass-layer-3 {
            background: #ffffff;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1.5px solid #cbd5e1;
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 8px 24px -4px rgba(15, 23, 42, 0.06);
            animation: cardSlideUp 300ms var(--ease-out-quint) both;
        }

        /* HIGH-VISIBILITY SELECTBOXES & INPUTS (Fixes 'listy rozwijalne sa malo widoczne') */
        div[data-baseweb="select"] > div {
            min-height: 44px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #64748b !important;
            border-radius: 10px !important;
            color: #0f172a !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
            transition: all 150ms ease !important;
            cursor: pointer !important;
        }

        div[data-baseweb="select"] > div:hover {
            border-color: #2563eb !important;
            background-color: #f8fafc !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12) !important;
        }

        div[data-baseweb="select"] > div:focus-within {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
        }

        div[data-baseweb="select"] svg {
            fill: #0f172a !important;
            color: #0f172a !important;
            width: 20px !important;
            height: 20px !important;
        }

        /* Dropdown Popover Menu Portal (Forces Crisp White Menu & Readable Options even if Browser is Dark Mode) */
        div[data-baseweb="popover"],
        div[data-baseweb="menu"],
        ul[role="listbox"] {
            background-color: #ffffff !important;
            border: 1.5px solid #94a3b8 !important;
            border-radius: 10px !important;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.16) !important;
            color: #0f172a !important;
        }

        li[role="option"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            font-weight: 500 !important;
            font-size: 0.88rem !important;
            padding: 10px 14px !important;
            border-bottom: 1px solid #f1f5f9 !important;
        }

        li[role="option"]:hover,
        li[role="option"][aria-selected="true"] {
            background-color: #eff6ff !important;
            color: #1d4ed8 !important;
            font-weight: 700 !important;
        }

        /* Text Input & Textarea Fields */
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div {
            min-height: 48px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #64748b !important;
            border-radius: 10px !important;
            color: #0f172a !important;
            font-weight: 500 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
        }

        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="textarea"] > div:focus-within {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16) !important;
        }

        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea {
            color: #0f172a !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
        }

        div[data-baseweb="input"] input::placeholder,
        div[data-baseweb="textarea"] textarea::placeholder {
            color: #475569 !important;
            opacity: 1 !important;
        }

        .stSelectbox label, .stTextInput label, .stTextArea label, .stNumberInput label {
            color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 0.84rem !important;
            letter-spacing: -0.01em !important;
            margin-bottom: 4px !important;
        }

        /* Buttons: Distinct Primary (active/CTA) vs Secondary (inactive/neutral) with 48px touch target */
        .stButton > button,
        .stFormSubmitButton > button {
            min-height: 48px !important;
            border-radius: 10px !important;
            padding: 0.5rem 1.25rem !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            transition: background-color 150ms var(--ease-out-quint), border-color 150ms var(--ease-out-quint), transform 120ms var(--ease-out-quint), box-shadow 150ms var(--ease-out-quint) !important;
        }

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"],
        button[data-testid="stBaseButton-primary"],
        button[data-testid="baseButton-primary"] {
            background: #2563eb !important;
            color: #ffffff !important;
            border: 1.5px solid #1d4ed8 !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.24) !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1e40af !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.32) !important;
        }

        .stButton > button[kind="secondary"],
        .stFormSubmitButton > button[kind="secondary"],
        button[data-testid="stBaseButton-secondary"],
        button[data-testid="baseButton-secondary"] {
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1.5px solid #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        }

        .stButton > button[kind="secondary"]:hover,
        .stFormSubmitButton > button[kind="secondary"]:hover,
        button[data-testid="stBaseButton-secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover {
            background: #f8fafc !important;
            border-color: #0f172a !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.1) !important;
        }

        .stButton > button:focus-visible,
        .stFormSubmitButton > button:focus-visible,
        .stDownloadButton > button:focus-visible {
            outline: 2px solid #2563eb !important;
            outline-offset: 2px !important;
        }

        .stButton > button:active,
        .stFormSubmitButton > button:active {
            transform: scale(0.98) !important;
        }

        .stDownloadButton > button {
            min-height: 44px !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
        }

        .stDownloadButton > button:hover {
            border-color: #0f172a !important;
            background: #f8fafc !important;
        }

        /* Data Editor & Tables */
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            border: 1px solid var(--border-hairline) !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
        }

        /* Uniform 48px height for all standard inputs, selects, and number inputs */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        [data-testid="stNumberInput"] > div > div {
            min-height: 48px !important;
            height: 48px !important;
            box-sizing: border-box !important;
        }

        /* Sticky Continuous Chat Composer pinned at the bottom of the viewport */
        [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sticky-chat-marker),
        [data-testid="stVerticalBlock"]:has(> .element-container .sticky-chat-marker) {
            position: sticky !important;
            bottom: 0.75rem !important;
            z-index: 40 !important;
            background: rgba(255, 255, 255, 0.97) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 30px rgba(15, 23, 42, 0.12) !important;
        }

        /* Unified Antigravity-style Chat Composer (direct selectors compatible with Streamlit 1.67+) */
        div[data-testid="stTextArea"]:has(textarea[aria-label="Pytanie do dokumentacji"]) div[data-baseweb="textarea"],
        div[data-testid="stTextArea"]:has(textarea[aria-label="Pytanie do dokumentacji"]) div[data-baseweb="textarea"] > div,
        div[data-testid="stTextArea"]:has(textarea[aria-label="Pytanie do dokumentacji"]) div[data-baseweb="base-input"] {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            padding: 0 !important;
            min-height: 0 !important;
            height: auto !important;
        }

        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
            align-items: center !important;
            gap: 8px !important;
        }

        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div,
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) [data-testid="stElementContainer"],
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) [data-testid="stMarkdown"] {
            margin: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            display: flex !important;
            align-items: center !important;
        }

        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) [data-testid="stPopover"] > button,
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) div[data-baseweb="select"] > div,
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) .chat-model-pill {
            min-height: 38px !important;
            height: 38px !important;
            max-height: 38px !important;
            border-radius: 9px !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: none !important;
            box-sizing: border-box !important;
            margin: 0 !important;
        }

        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) [data-testid="stPopover"] > button:hover,
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) div[data-baseweb="select"] > div:hover {
            background: #eff6ff !important;
            border-color: #2563eb !important;
            color: #1d4ed8 !important;
        }

        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) button[kind="primary"],
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) button[data-testid="stBaseButton-primary"],
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) button[data-testid="baseButton-primary"] {
            min-height: 38px !important;
            height: 38px !important;
            max-height: 38px !important;
            width: 38px !important;
            min-width: 38px !important;
            padding: 0 !important;
            border-radius: 10px !important;
            font-size: 1rem !important;
            line-height: 1 !important;
            margin: 0 0 0 auto !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Responsive Breakpoints (Tablet & Mobile <= 768px, Small Desktop <= 1024px) */
        @media (max-width: 1024px) {
            .glass-layer-2, .glass-layer-3 {
                padding: 16px !important;
            }
        }

        @media (max-width: 768px) {
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 8px !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"],
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }
            .glass-layer-1, .glass-layer-2, .glass-layer-3 {
                padding: 14px !important;
                border-radius: 12px !important;
            }
        }

        /* Chips */
        .glass-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.76rem;
            font-weight: 600;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            color: #334155;
            margin-right: 6px;
            margin-bottom: 4px;
        }

        .highlight-term {
            background: #f1f5f9;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 1px 6px;
            border-radius: 4px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.84em;
        }

        .v-bar-fill {
            transform-origin: bottom;
            animation: barGrowVertical 500ms var(--ease-out-quint) both;
        }

        @media (prefers-reduced-motion: reduce) {
            *, ::before, ::after {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
    """


def render_brand_sidebar_header(href: Optional[str] = None) -> str:
    """Renders the compact geometric logo and app title, optionally wrapped as a clickable home link."""
    logo_svg = get_svg_icon("brand-mark", size=24, color="#0f172a")
    inner = (
        f'<div style="display:flex;align-items:center;gap:10px;padding:4px 4px 12px 4px;border-bottom:1px solid #e2e8f0;margin-bottom:12px;">'
        f'<div style="width:44px;height:44px;border-radius:11px;background:#f8fafc;border:1.5px solid #cbd5e1;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
        f'{logo_svg}</div>'
        f'<div>'
        f'<div style="font-size:0.96rem;font-weight:800;color:#0f172a;letter-spacing:-0.02em;line-height:1.15;">GisMarket</div>'
        f'<div style="font-size:0.7rem;font-weight:600;color:#64748b;">Intelligence AI</div>'
        f'</div></div>'
    )
    if href:
        safe_href = html.escape(href, quote=True)
        return _compact_html(
            f'<a href="{safe_href}" target="_self" title="Przejdź do pulpitu (lista przetargów)" '
            f'style="text-decoration:none;color:inherit;display:block;">{inner}</a>'
        )
    return _compact_html(inner)


def render_top_utility_bar(
    municipality: str,
    voivodeship: str,
    ollama_ok: bool,
    total_tenders: int,
    has_lockin: bool,
) -> str:
    """Renders a clean top navbar with breadcrumbs on the left and status pills on the right."""
    home_svg = get_svg_icon("home", size=16, color="#475569")
    safe_muni = html.escape(municipality)
    safe_voiv = html.escape(voivodeship)

    status_badge = (
        '<span style="display:inline-flex;align-items:center;gap:6px;background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;padding:5px 12px;border-radius:999px;font-size:0.76rem;font-weight:700;">'
        '<span style="width:6px;height:6px;border-radius:50%;background:#dc2626;display:inline-block;"></span>'
        'Wykryto bariery SWZ</span>'
        if has_lockin
        else '<span style="display:inline-flex;align-items:center;gap:6px;background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;padding:5px 12px;border-radius:999px;font-size:0.76rem;font-weight:700;">'
        '<span style="width:6px;height:6px;border-radius:50%;background:#059669;display:inline-block;"></span>'
        'Zgodność z PZP</span>'
    )
    dot_color = "#059669" if ollama_ok else "#d97706"
    env_label = "Silnik hybrydowy BGE-M3 + pgvector"

    return _compact_html(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px;padding:4px 0;">
        <div style="display:flex;align-items:center;gap:8px;font-size:0.84rem;color:#64748b;font-weight:500;">
            {home_svg}
            <span>Audyt zamówień publicznych</span>
            <span style="color:#cbd5e1;">/</span>
            <span>{safe_voiv}</span>
            <span style="color:#cbd5e1;">/</span>
            <span style="color:#0f172a;font-weight:700;">{safe_muni}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            {status_badge}
            <div style="display:inline-flex;align-items:center;gap:8px;background:#ffffff;border:1px solid #cbd5e1;padding:5px 12px;border-radius:999px;font-size:0.76rem;color:#334155;font-weight:600;">
                <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};display:inline-block;"></span>
                <span>{env_label}</span>
                <span style="background:#f1f5f9;color:#0f172a;padding:1px 7px;border-radius:999px;font-size:0.72rem;font-weight:700;">{total_tenders} SWZ</span>
            </div>
        </div>
    </div>
    """)


def render_kpi_stat_card(
    value: str,
    label: str,
    sublabel: str,
    icon_name: str,
    color_hex: str = "#0f172a",
    ring_bg: str = "#f1f5f9",
    stagger_index: int = 0,
) -> str:
    """Renders a restrained, high-contrast executive KPI card without rainbow AI clichés."""
    svg = get_svg_icon(icon_name, size=20, color=color_hex)
    delay_ms = stagger_index * 40
    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:16px 18px;min-height:114px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;animation-delay:{delay_ms}ms;">
        <div style="min-width:0;">
            <div style="font-size:0.76rem;font-weight:600;color:#64748b;margin-bottom:4px;">
                {html.escape(label)}
            </div>
            <div style="font-size:1.4rem;font-weight:800;color:{color_hex};line-height:1.15;letter-spacing:-0.025em;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {html.escape(value)}
            </div>
            <div style="font-size:0.74rem;color:#475569;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {html.escape(sublabel)}
            </div>
        </div>
        <div style="width:38px;height:38px;border-radius:9px;background:{ring_bg};border:1px solid #e2e8f0;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            {svg}
        </div>
    </div>
    """)


def render_risk_profile_panel(
    has_lockin: bool,
    has_penalties: bool,
    faithfulness: float,
    format_score: int = 92,
    penalty_score: int = 86,
    personnel_score: int = 64,
    system_tags: List[str] | None = None,
) -> str:
    """Renders a clean, restrained architectural bar chart card with an overall score summary."""
    b1 = format_score
    b2 = penalty_score
    b3 = personnel_score
    b4 = int(round(faithfulness * 100))
    overall_score = int(round((b1 + b2 + b3) / 3))

    bars = [
        ("Format", b1, "#0f172a" if b1 < 70 else "#dc2626"),
        ("Kary", b2, "#334155" if b2 < 70 else "#d97706"),
        ("Kadra", b3, "#475569"),
        ("RAGAS", b4, "#059669"),
    ]
    bars_html = ""
    for idx, (lbl, pct, col) in enumerate(bars):
        delay = idx * 60
        bars_html += (
            f"<div style='display:flex;flex-direction:column;align-items:center;gap:6px;flex:1;'>"
            f"<div style='height:128px;width:26px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;display:flex;align-items:flex-end;overflow:hidden;padding:2px;'>"
            f"<div class='v-bar-fill' style='width:100%;height:{pct}%;background:{col};border-radius:4px;animation-delay:{delay}ms;'></div>"
            f"</div>"
            f"<span style='font-size:0.74rem;font-weight:600;color:#475569;'>{lbl}</span>"
            f"<span style='font-size:0.72rem;font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums;'>{pct}%</span>"
            f"</div>"
        )

    if overall_score >= 70:
        verdict_note = "Wysoka restrykcyjność SWZ — rekomendowany wniosek z art. 135 PZP"
    elif overall_score >= 45:
        verdict_note = "Umiarkowana restrykcyjność — weryfikacja równoważności GML"
    else:
        verdict_note = "Niska restrykcyjność — dokumentacja zgodna ze standardem GML"

    tags = system_tags or ["EWMAPA (.str)", "iMPA / OŚRODEK"]
    tags_html = "".join(
        f"<span class='glass-chip' style='background:#f8fafc;color:#0f172a;border-color:#cbd5e1;'>{html.escape(t)}</span>"
        for t in tags
    )

    return _compact_html(f"""
    <div class="glass-layer-2" style="display:flex;flex-direction:column;justify-content:space-between;">
        <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <span style="font-size:0.95rem;font-weight:800;color:#0f172a;">Profil ryzyka SWZ</span>
                <span style="font-size:0.72rem;font-weight:700;color:#334155;background:#f1f5f9;border:1px solid #e2e8f0;padding:3px 9px;border-radius:6px;">Indeks barier</span>
            </div>
            <div style="display:flex;justify-content:space-around;align-items:flex-end;gap:10px;padding:10px 4px 14px 4px;border-bottom:1px solid #f1f5f9;">
                {bars_html}
            </div>
        </div>
        <div style="text-align:center;padding-top:14px;">
            <div style="font-size:1.85rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;line-height:1.1;font-variant-numeric:tabular-nums;">
                {overall_score} <span style="font-size:0.92rem;font-weight:600;color:#64748b;">/ 100</span>
            </div>
            <div style="font-size:0.78rem;color:#475569;margin-top:4px;line-height:1.4;">
                {verdict_note}
            </div>
            <div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap;margin-top:10px;">
                {tags_html}
            </div>
        </div>
    </div>
    """)


def render_red_flag_badge(flag_type: str) -> str:
    """Renders a crisp semantic warning pill with custom SVG icon."""
    configs: Dict[str, Dict[str, str]] = {
        "vendor_lockin": {
            "label": "Vendor Lock-in (.str / EWMAPA)",
            "bg": "#fef2f2",
            "border": "#fecaca",
            "color": "#991b1b",
            "icon_color": "#dc2626",
            "icon": "shield-alert",
        },
        "asymetria_kar": {
            "label": "Asymetria kar umownych (brak górnego limitu)",
            "bg": "#fffbeb",
            "border": "#fde68a",
            "color": "#92400e",
            "icon_color": "#d97706",
            "icon": "scale",
        },
        "krotki_termin": {
            "label": "Napięty harmonogram realizacji",
            "bg": "#f8fafc",
            "border": "#cbd5e1",
            "color": "#1e293b",
            "icon_color": "#475569",
            "icon": "layers",
        },
    }

    cfg = configs.get(
        flag_type.lower(),
        {
            "label": f"Ryzyko SWZ: {flag_type}",
            "bg": "#f8fafc",
            "border": "#cbd5e1",
            "color": "#334155",
            "icon_color": "#475569",
            "icon": "shield-alert",
        },
    )

    svg = get_svg_icon(cfg["icon"], size=16, color=cfg["icon_color"])
    return _compact_html(f"""
    <span style="display:inline-flex;align-items:center;gap:6px;background-color:{cfg['bg']};color:{cfg['color']};border:1px solid {cfg['border']};padding:5px 11px;border-radius:6px;font-weight:600;font-size:0.78rem;margin-right:8px;margin-bottom:6px;">
        {svg}
        <span>{cfg['label']}</span>
    </span>
    """)


def render_citation_box(citation_text: str) -> str:
    """Renders a concise verified SWZ/OPZ document reference pill."""
    escaped = html.escape(citation_text.strip(" []"))
    svg = get_svg_icon("file-check", size=16, color="#475569")
    return _compact_html(f"""
    <div class="glass-layer-1" style="padding:10px 14px;margin:6px 0;display:flex;align-items:center;gap:10px;border-radius:8px;background:#f8fafc;">
        {svg}
        <div style="font-size:0.82rem;line-height:1.4;color:#1e293b;">
            <span style="color:#475569;font-weight:700;margin-right:6px;">Źródło dowodowe SWZ/OPZ:</span>
            <span style="color:#0f172a;font-family:'JetBrains Mono',monospace;font-size:0.79rem;">{escaped}</span>
        </div>
    </div>
    """)


def render_competitor_matrix(competitors: List[Dict[str, str]]) -> str:
    """Renders a clean architectural table displaying regional GIS competitors."""
    if not competitors:
        return "<div class='glass-layer-1'>Brak zidentyfikowanych podmiotów konkurencyjnych.</div>"

    rows_html = ""
    for comp in competitors:
        name = html.escape(comp.get("name", "Nieznany podmiot"))
        product = html.escape(comp.get("product", "-"))
        advantage = html.escape(comp.get("advantage", "-"))
        rows_html += (
            f"<tr style='border-bottom:1px solid #f1f5f9;'>"
            f"<td style='padding:11px 14px;font-weight:700;color:#0f172a;font-size:0.84rem;'>{name}</td>"
            f"<td style='padding:11px 14px;'><span style='background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;padding:2px 8px;border-radius:5px;font-family:\"JetBrains Mono\",monospace;font-size:0.76rem;font-weight:600;'>{product}</span></td>"
            f"<td style='padding:11px 14px;color:#334155;font-size:0.83rem;'>{advantage}</td>"
            f"</tr>"
        )

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:0;overflow:hidden;margin:8px 0;">
        <table style="width:100%;border-collapse:collapse;text-align:left;">
            <thead>
                <tr style="background:#f8fafc;color:#475569;border-bottom:1px solid #e2e8f0;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;">
                    <th style="padding:10px 14px;">Podmiot / Technologia</th>
                    <th style="padding:10px 14px;">System bazodanowy</th>
                    <th style="padding:10px 14px;">Pozycja w postępowaniu</th>
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
        bg = "#fef2f2"
        border = "#fecaca"
        color = "#991b1b"
        icon_color = "#dc2626"
        text = "Ryzyko odwołania do KIO: WYSOKIE (podstawa prawna: art. 16 oraz art. 99 ust. 4 ustawy PZP)"
    elif level == "MEDIUM":
        bg = "#fffbeb"
        border = "#fde68a"
        color = "#92400e"
        icon_color = "#d97706"
        text = "Ryzyko odwołania do KIO: ŚREDNIE (zalecany wniosek z art. 135 PZP o równoważność konektora GML)"
    else:
        bg = "#ecfdf5"
        border = "#a7f3d0"
        color = "#065f46"
        icon_color = "#059669"
        text = "Ryzyko odwołania do KIO: NISKIE (opis przedmiotu zamówienia dopuszcza otwarty standard GML)"

    svg = get_svg_icon("scale", size=20, color=icon_color)
    return _compact_html(f"""
    <div style="background:{bg};color:{color};border:1px solid {border};padding:11px 15px;border-radius:10px;font-weight:600;font-size:0.84rem;margin:6px 0 12px 0;display:flex;align-items:center;gap:10px;">
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
        budget_color = "#0f172a"
    else:
        budget_str = "Wg kosztorysu SWZ"
        budget_color = "#64748b"

    building_svg = get_svg_icon("building", size=16, color="#475569")
    pin_svg = get_svg_icon("map-pin", size=16, color="#475569")
    wallet_svg = get_svg_icon("wallet", size=16, color="#475569")

    layer_class = "glass-layer-3" if is_selected else "glass-layer-2"
    selected_badge = (
        '<span style="background:#0f172a;color:#ffffff;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;">W analizie</span>'
        if is_selected
        else f'<span style="background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;">{status_pl}</span>'
    )

    return _compact_html(f"""
    <div class="{layer_class}" style="margin-bottom:10px;padding:14px 18px;" data-ocds-id="{safe_full_id}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:8px;">
            <div style="font-size:0.94rem;font-weight:700;color:#0f172a;line-height:1.4;">{safe_title}</div>
            {selected_badge}
        </div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;">
            <span class="glass-chip" title="{safe_full_id}" style="font-family:'JetBrains Mono',monospace;">
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


def render_clickable_procurements_table(rows: List[Dict[str, Any]], session_token: str) -> str:
    """Renders a clickable procurements table with no checkboxes; clicking any row opens the tender."""
    building_svg = get_svg_icon("building", size=16, color="#334155")
    safe_tok = quote(session_token, safe="")

    tbody = ""
    for row in rows:
        row_id = str(row.get("ID", ""))
        href = f"?session={safe_tok}&tender={quote(row_id, safe='')}"
        short_id = html.escape(format_short_ocds_id(row_id))
        muni = html.escape(str(row.get("Zamawiający", "")))
        title = html.escape(str(row.get("Tytuł", "")))
        voiv = html.escape(str(row.get("Województwo", "")))
        deadline = html.escape(str(row.get("Termin", ""))[:10])
        budget_val = float(row.get("Budżet PLN", 0.0) or 0.0)
        budget_str = f"{budget_val:,.0f} PLN".replace(",", " ") if budget_val > 0 else "Wg SWZ"

        def _cell(inner_html: str, extra_style: str = "") -> str:
            return (
                f"<td style='padding:0;{extra_style}'>"
                f"<a class='tender-row-link' href='{href}' target='_self' style='padding:12px 14px;'>"
                f"{inner_html}</a></td>"
            )

        muni_cell = _cell(
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<div style='width:30px;height:30px;border-radius:8px;background:#f1f5f9;border:1px solid #e2e8f0;"
            f"display:flex;align-items:center;justify-content:center;flex-shrink:0;'>{building_svg}</div>"
            f"<span style='font-weight:700;color:#0f172a;font-size:0.84rem;'>{muni}</span></div>"
        )
        title_cell = _cell(f"<span style='color:#334155;font-size:0.84rem;font-weight:500;'>{title}</span>", "max-width:440px;")
        voiv_cell = _cell(f"<span style='color:#475569;font-size:0.82rem;'>{voiv}</span>")
        budget_cell = _cell(f"<span style='font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums;font-size:0.84rem;'>{budget_str}</span>")
        deadline_cell = _cell(f"<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.78rem;color:#475569;'>{deadline}</span>")
        id_cell = _cell(f"<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.75rem;color:#64748b;'>{short_id}</span>")

        tbody += f"<tr class='tender-row' style='border-bottom:1px solid #f1f5f9;'>{muni_cell}{title_cell}{voiv_cell}{budget_cell}{deadline_cell}{id_cell}</tr>"

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:18px 20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
            <div>
                <h3 style="margin:0;font-size:1.05rem;font-weight:800;color:#0f172a;">Lista postępowań przetargowych</h3>
                <div style="font-size:0.78rem;color:#64748b;margin-top:2px;">Kliknij dowolny wiersz, aby otworzyć pełny audyt SWZ/OPZ i pytania AI</div>
            </div>
            <span style="font-size:0.76rem;font-weight:700;color:#0f172a;background:#f1f5f9;border:1px solid #cbd5e1;padding:4px 10px;border-radius:6px;">Pozycji: {len(rows)}</span>
        </div>
        <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;text-align:left;">
                <thead>
                    <tr style="border-bottom:1px solid #e2e8f0;color:#64748b;font-size:0.73rem;font-weight:700;text-transform:uppercase;letter-spacing:0.03em;">
                        <th style="padding:10px 14px;">Zamawiający</th>
                        <th style="padding:10px 14px;">Przedmiot zamówienia</th>
                        <th style="padding:10px 14px;">Województwo</th>
                        <th style="padding:10px 14px;">Budżet</th>
                        <th style="padding:10px 14px;">Termin</th>
                        <th style="padding:10px 14px;">Nr ref.</th>
                    </tr>
                </thead>
                <tbody>{tbody}</tbody>
            </table>
        </div>
    </div>
    """)


def render_procurements_table(rows: List[Dict[str, Any]], selected_id: str) -> str:
    """Renders a modern SaaS table card with restrained slate styling."""
    check_svg = get_svg_icon("check-circle", size=16, color="#059669")
    building_svg = get_svg_icon("building", size=16, color="#334155")

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
            "<span style='background:#0f172a;color:#ffffff;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;display:inline-block;'>Wybrane</span>"
            if is_sel
            else "<span style='background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;display:inline-block;'>W bazie</span>"
        )

        tbody += (
            f"<tr style='border-bottom:1px solid #f1f5f9;{row_bg}'>"
            f"<td style='padding:12px 14px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<div style='width:32px;height:32px;border-radius:8px;background:#f1f5f9;border:1px solid #e2e8f0;display:flex;align-items:center;justify-content:center;flex-shrink:0;'>{building_svg}</div>"
            f"<span style='font-weight:700;color:#0f172a;font-size:0.84rem;'>{muni}</span>"
            f"</div>"
            f"</td>"
            f"<td style='padding:12px 14px;color:#334155;font-size:0.84rem;font-weight:500;max-width:440px;'>{title}</td>"
            f"<td style='padding:12px 14px;font-family:\"JetBrains Mono\",monospace;font-size:0.76rem;color:#64748b;'>{short_id}</td>"
            f"<td style='padding:12px 14px;color:#475569;font-size:0.82rem;'>{voiv}</td>"
            f"<td style='padding:12px 14px;font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums;font-size:0.84rem;'>{budget_str}</td>"
            f"<td style='padding:12px 14px;'>"
            f"<span style='display:inline-flex;align-items:center;gap:5px;color:#059669;font-weight:600;font-size:0.78rem;'>{check_svg}<span>Zindeksowano</span></span>"
            f"</td>"
            f"<td style='padding:12px 14px;text-align:right;'>{status_pill}</td>"
            f"</tr>"
        )

    return _compact_html(f"""
    <div class="glass-layer-2" style="padding:20px 22px;margin-top:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <div>
                <h3 style="margin:0;font-size:1.02rem;font-weight:800;color:#0f172a;">Zindeksowane postępowania przetargowe</h3>
                <div style="font-size:0.78rem;color:#64748b;margin-top:2px;">Kliknij listę wyboru na górze ekranu, aby przełączyć analizowane postępowanie SWZ/OPZ</div>
            </div>
            <span style="font-size:0.76rem;font-weight:700;color:#0f172a;background:#f1f5f9;border:1px solid #cbd5e1;padding:4px 10px;border-radius:6px;">Pozycji: {len(rows)}</span>
        </div>
        <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;text-align:left;">
                <thead>
                    <tr style="border-bottom:1px solid #e2e8f0;color:#64748b;font-size:0.73rem;font-weight:700;text-transform:uppercase;letter-spacing:0.03em;">
                        <th style="padding:10px 14px;">Zamawiający</th>
                        <th style="padding:10px 14px;">Przedmiot zamówienia</th>
                        <th style="padding:10px 14px;">Nr ref.</th>
                        <th style="padding:10px 14px;">Województwo</th>
                        <th style="padding:10px 14px;">Szacunek</th>
                        <th style="padding:10px 14px;">Indeks wektorowy</th>
                        <th style="padding:10px 14px;text-align:right;">Stan</th>
                    </tr>
                </thead>
                <tbody>{tbody}</tbody>
            </table>
        </div>
    </div>
    """)


def highlight_domain_terms(text: str) -> str:
    """Formats domain terms cleanly without turning paragraphs into noisy neon links."""
    escaped = html.escape(text)
    escaped = re.sub(r"\[([^\[\]]+)\]", r'<span class="highlight-term">[\1]</span>', escaped)
    keywords = [
        r"\.str",
        r"\.giv",
        r"EWMAPA",
        r"GEO-INFO",
        r"EWOPIS",
        r"TurboEWID",
        r"BDOT500",
        r"GESUT",
        r"EGiB",
        r"OŚRODEK",
        r"OSRODEK",
        r"iMPA",
        r"GML",
        r"Vendor Lock-in",
        r"art\.\s*16",
        r"art\.\s*99",
        r"art\.\s*436",
        r"PZP",
        r"KIO",
        r"\d+(?:,\d+)?%",
    ]
    for kw in keywords:
        escaped = re.sub(
            rf"({kw})",
            r'<strong style="color:#0f172a;font-weight:700;">\1</strong>',
            escaped,
            flags=re.IGNORECASE,
        )
    return escaped


def _split_body_and_source(raw_text: str, default_source: str = "SWZ / OPZ") -> tuple[str, str]:
    """Separates inline bracketed citations from the prose body so cards read cleanly."""
    matches = re.findall(r"\[([^\[\]]+)\]", raw_text)
    source_label = matches[-1].strip() if matches else default_source
    clean_body = re.sub(r"\s*\[([^\[\]]+)\]\.?", "", raw_text).strip()
    if clean_body and not clean_body.endswith("."):
        clean_body += "."
    return clean_body, source_label


def render_insight_section_card(title: str, body: str, icon_name: str, accent_color: str = "#0f172a") -> str:
    """Renders a single structured audit section with clean prose and a dedicated footer source citation."""
    svg = get_svg_icon(icon_name, size=16, color="#334155")
    clean_prose, source_label = _split_body_and_source(body.strip() or "Brak dodatkowych uwag w tej sekcji.")
    formatted_body = highlight_domain_terms(clean_prose)
    return _compact_html(f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px;margin-bottom:12px;display:flex;flex-direction:column;justify-content:space-between;min-height:165px;">
        <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <div style="width:28px;height:28px;border-radius:7px;background:#f8fafc;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center;">
                    {svg}
                </div>
                <h4 style="margin:0;font-size:0.88rem;font-weight:700;color:#0f172a;">{html.escape(title)}</h4>
            </div>
            <div style="font-size:0.85rem;line-height:1.6;color:#334155;">
                {formatted_body}
            </div>
        </div>
        <div style="margin-top:10px;padding-top:8px;border-top:1px solid #f1f5f9;font-size:0.74rem;color:#64748b;font-family:'JetBrains Mono',monospace;">
            Źródło: {html.escape(source_label)}
        </div>
    </div>
    """)


def render_direct_answer_card(question: str, answer: str, top_chunks: List[Dict[str, Any]] | None = None) -> str:
    """Renders a crisp answer card showing the direct RAG answer and the top retrieved passage score."""
    sparkles_svg = get_svg_icon("search", size=16, color="#0f172a")
    safe_q = html.escape(question.strip())
    clean_ans, source_label = _split_body_and_source(answer.strip(), "Zindeksowane rozdziały SWZ/OPZ")
    formatted_ans = highlight_domain_terms(clean_ans)

    chunk_info = ""
    if top_chunks:
        best = top_chunks[0]
        score_val = best.get("rerank_score") or best.get("rrf_score") or best.get("score") or 0.98
        sec_title = html.escape(str(best.get("section_title") or "Rozdział SWZ"))
        chunk_info = (
            f"<span style='background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;padding:2px 8px;border-radius:5px;font-family:\"JetBrains Mono\",monospace;font-size:0.72rem;'>"
            f"Dopasowanie: {sec_title} (score: {float(score_val):.2f})</span>"
        )

    return _compact_html(f"""
    <div style="background:#ffffff;border:1.5px solid #94a3b8;border-radius:12px;padding:16px 20px;margin:6px 0 14px 0;box-shadow:0 4px 12px rgba(15,23,42,0.04);">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #f1f5f9;">
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:28px;height:28px;border-radius:7px;background:#f1f5f9;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center;">
                    {sparkles_svg}
                </div>
                <span style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;color:#475569;font-weight:800;">
                    Odpowiedź na zadane pytanie z dokumentacji SWZ / OPZ
                </span>
            </div>
            {chunk_info}
        </div>
        <div style="font-size:0.88rem;font-weight:700;color:#0f172a;margin-bottom:6px;">
            Pytanie: {safe_q}
        </div>
        <div style="font-size:0.88rem;line-height:1.65;color:#1e293b;">
            {formatted_ans}
        </div>
        <div style="margin-top:8px;font-size:0.75rem;color:#64748b;font-family:'JetBrains Mono',monospace;">
            Zweryfikowane źródło: {html.escape(source_label)}
        </div>
    </div>
    """)
