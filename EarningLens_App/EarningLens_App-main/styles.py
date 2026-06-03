"""
styles.py
Global CSS — dark financial terminal aesthetic with vivid accents.
Syne display font + DM Mono for data. Confident, spacious, memorable.
"""

# ── Minimal CSS injected on every page BEFORE auth check ──────────────────────
# Use this on login + any unauthenticated page to suppress the sidebar flash.
HIDE_NAV_CSS = """
<style>
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] nav,
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"] {
    display: none !important;
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
</style>
"""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & base ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080e1a !important;
    color: #e8eaf0 !important;
}

/* ── App background ────────────────────────────────────────── */
.main .block-container {
    padding-top: 32px;
    padding-bottom: 60px;
    max-width: 1380px;
    background: #080e1a;
}

/* Subtle grid texture on main bg */
.main {
    background-image:
        linear-gradient(rgba(99,179,237,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(99,179,237,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* ── Sidebar ───────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0d1526 !important;
    border-right: 1px solid rgba(99,179,237,0.12) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] * {
    color: #c8d0e0 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMarkdown p {
    font-size: 11px !important;
    font-family: 'DM Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #5d7a99 !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #111e35 !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 6px !important;
    color: #e8eaf0 !important;
}

/* ── Section headings ──────────────────────────────────────── */
h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #63b3ed !important;
    margin-bottom: 14px !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid rgba(99,179,237,0.15) !important;
}

/* ── Dataframe / table ─────────────────────────────────────── */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid rgba(99,179,237,0.15) !important;
    background: #0d1526 !important;
}
.stDataFrame thead tr th {
    background: #111e35 !important;
    color: #63b3ed !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    border-bottom: 2px solid rgba(99,179,237,0.25) !important;
}
.stDataFrame tbody tr {
    background: #0d1526 !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
}
.stDataFrame tbody tr:hover {
    background: #14253d !important;
}
.stDataFrame tbody tr td {
    color: #d0d8ea !important;
    font-size: 13px !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Buttons ───────────────────────────────────────────────── */
.stDownloadButton > button {
    background: transparent !important;
    color: #63b3ed !important;
    border: 1px solid rgba(99,179,237,0.4) !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.5px;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover {
    background: rgba(99,179,237,0.12) !important;
    border-color: #63b3ed !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1a56db, #0ea5e9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 1px;
    padding: 10px 28px !important;
    transition: opacity 0.2s ease !important;
    box-shadow: 0 0 20px rgba(14,165,233,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.88 !important;
}

/* ── Text inputs ───────────────────────────────────────────── */
.stTextInput input {
    background: #111e35 !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 6px !important;
    color: #e8eaf0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}
.stTextInput input:focus {
    border-color: #63b3ed !important;
    box-shadow: 0 0 0 2px rgba(99,179,237,0.15) !important;
}
.stTextInput input::placeholder { color: #3d5a7a !important; }

/* ── Expander ──────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #111e35 !important;
    border: 1px solid rgba(99,179,237,0.15) !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    color: #63b3ed !important;
    letter-spacing: 0.5px;
}
.streamlit-expanderContent {
    background: #0d1526 !important;
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 6px 6px !important;
}

/* ── Caption / small text ──────────────────────────────────── */
.stCaption, small, .caption {
    color: #3d5a7a !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
}

/* ── Spinner ───────────────────────────────────────────────── */
.stSpinner > div {
    border-color: #63b3ed transparent transparent transparent !important;
}

/* ── Divider ───────────────────────────────────────────────── */
hr {
    border-color: rgba(99,179,237,0.12) !important;
}

/* ── Info / warning boxes ──────────────────────────────────── */
.stInfo {
    background: rgba(14,165,233,0.08) !important;
    border-left-color: #0ea5e9 !important;
    color: #93c5fd !important;
}
.stWarning {
    background: rgba(245,158,11,0.08) !important;
    border-left-color: #f59e0b !important;
}

/* ── Hide Streamlit chrome + default page nav ──────────────── */
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Hide auto-generated sidebar page links */
section[data-testid="stSidebar"] nav,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
    display: none !important;
}

/* Sign-out button */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #3d5a7a !important;
    border: 1px solid rgba(99,179,179,0.12) !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.5px !important;
    padding: 7px 14px !important;
    transition: all 0.2s ease !important;
    text-align: left !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(248,113,113,0.08) !important;
    border-color: rgba(248,113,113,0.3) !important;
    color: #f87171 !important;
}
</style>
"""

# ── Sidebar logo / header HTML ─────────────────────────────────────────────────
SIDEBAR_HEADER = """
<div style="
    background: linear-gradient(135deg, #0a1628 0%, #0d2040 100%);
    border-bottom: 1px solid rgba(99,179,237,0.15);
    padding: 28px 20px 22px 20px;
    margin: -1rem -1rem 1.5rem -1rem;
">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-size:22px;">🔭</span>
    <span style="
        font-family:'Syne',sans-serif;
        font-size:20px;
        font-weight:800;
        color:#e8eaf0;
        letter-spacing:1px;
    ">EarningsLens</span>
  </div>
  <p style="
    margin:0;
    font-family:'DM Mono',monospace;
    font-size:10px;
    color:#3d5a7a;
    letter-spacing:1.5px;
    text-transform:uppercase;
  ">Guidance Intelligence Platform</p>
</div>
"""

# ── Inline feedback message helpers ───────────────────────────────────────────
def msg_error(text: str) -> str:
    return f"""
<div style="
    display:flex;align-items:center;gap:10px;
    background:rgba(248,113,113,0.08);
    border:1px solid rgba(248,113,113,0.25);
    border-radius:8px;padding:10px 14px;margin-top:14px;
">
  <span style="font-size:15px;">✕</span>
  <span style="font-family:'DM Sans',sans-serif;font-size:13px;color:#fca5a5;">{text}</span>
</div>"""

def msg_success(text: str) -> str:
    return f"""
<div style="
    display:flex;align-items:center;gap:10px;
    background:rgba(34,211,165,0.07);
    border:1px solid rgba(34,211,165,0.25);
    border-radius:8px;padding:10px 14px;margin-top:14px;
">
  <span style="font-size:15px;">✓</span>
  <span style="font-family:'DM Sans',sans-serif;font-size:13px;color:#6ee7b7;">{text}</span>
</div>"""

def msg_warning(text: str) -> str:
    return f"""
<div style="
    display:flex;align-items:center;gap:10px;
    background:rgba(245,158,11,0.07);
    border:1px solid rgba(245,158,11,0.25);
    border-radius:8px;padding:10px 14px;margin-top:14px;
">
  <span style="font-size:15px;">⚠</span>
  <span style="font-family:'DM Sans',sans-serif;font-size:13px;color:#fcd34d;">{text}</span>
</div>"""