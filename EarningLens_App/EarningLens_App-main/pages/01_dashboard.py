"""
pages/01_dashboard.py — Main dashboard (authenticated users only)
"""
import streamlit as st
st.set_page_config(
    page_title="EarningsLens",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auth check — zero imports before this
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user"):
    st.switch_page("app.py")
    st.stop()

# All heavy imports only run for authenticated users
import pandas as pd
import styles
import auth_client
from supabase_client import (
    get_companies,
    fetch_commitments,
    fetch_summary,
    fetch_credibility_summary,
)
from agent import generate_alert
from rag import answer_question, rag_status
from ui_components import (
    render_alert_banner,
    render_guidance_table,
    render_hedge_chart,
    render_summary_box,
    render_kpi_strip,
)

user = st.session_state.get("user")

st.markdown(styles.GLOBAL_CSS, unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(styles.SIDEBAR_HEADER, unsafe_allow_html=True)

    companies_df = get_companies()
    def _label(row):
        name = str(row.get("company_name") or "").strip()
        return f"{row['ticker']}  —  {name}" if name and name.lower() != "none" else row["ticker"]

    company_options = {_label(row): row["ticker"] for _, row in companies_df.iterrows()}
    selected_label  = st.selectbox("COMPANY", list(company_options.keys()), index=0)
    selected_ticker = company_options[selected_label]

    QUARTERS = (
        [f"Q{q} {y}" for y in [2023, 2024] for q in range(1, 5)]
        + ["Q1 2025"]
    )
    selected_quarter = st.selectbox("QUARTER", QUARTERS, index=4)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-family:\'DM Mono\',monospace;font-size:10px;'
        'color:#1e3a5f;letter-spacing:1px;">531 S&P 500 companies · Q1 2023 – Q1 2025</p>',
        unsafe_allow_html=True,
    )

    user_meta = getattr(user, "user_metadata", {}) or {}
    display_name = (
        user_meta.get("full_name")
        or user_meta.get("name")
        or getattr(user, "email", "")
        or ""
    )

    st.markdown(f"""
    <div style="margin-top:28px;border-top:1px solid rgba(99,179,237,0.1);padding-top:18px;">
      <p style="font-family:'DM Mono',monospace;font-size:10px;color:#2a4a6a;
                letter-spacing:1px;text-transform:uppercase;margin:0 0 6px;">Signed in as</p>
      <div style="font-family:'DM Sans',sans-serif;font-size:13px;font-weight:500;
                  color:#63b3ed;margin-bottom:14px;overflow:hidden;
                  text-overflow:ellipsis;white-space:nowrap;">{display_name}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⎋  Sign out", use_container_width=True):
        auth_client.sign_out()
        st.switch_page("app.py")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("📄  Upload New Transcript", use_container_width=True):
        st.switch_page("pages/05_upload_transcript.py")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    _rs = rag_status()
    _rag_colour = "#22d3a5" if (_rs["faiss_ok"] and _rs["embedder_ok"]) else "#f59e0b"
    _rag_icon   = "●" if (_rs["faiss_ok"] and _rs["embedder_ok"]) else "○"
    st.markdown(
        f'<p style="font-family:\'DM Mono\',monospace;font-size:10px;'
        f'color:{_rag_colour};letter-spacing:1px;">'
        f'{_rag_icon} {_rs["message"]}</p>',
        unsafe_allow_html=True,
    )

# ── Parse quarter ──────────────────────────────────────────────────────────────
q_num  = int(selected_quarter[1])
q_year = int(selected_quarter[3:])

# ── Cached data loaders ────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _commitments(ticker, q, y):  return fetch_commitments(ticker, q, y)

@st.cache_data(ttl=300, show_spinner=False)
def _summary(ticker, q, y):      return fetch_summary(ticker, q, y)

@st.cache_data(ttl=300, show_spinner=False)
def _credibility(ticker):         return fetch_credibility_summary(ticker)

@st.cache_data(ttl=600, show_spinner=False)
def _alert(ticker, q, y):        return generate_alert(ticker, q, y)

with st.spinner(""):
    commitments_df = _commitments(selected_ticker, q_num, q_year)
    summary_text   = _summary(selected_ticker, q_num, q_year)
    cred           = _credibility(selected_ticker)
    alert          = _alert(selected_ticker, q_num, q_year)

# ── Page header ────────────────────────────────────────────────────────────────
ticker_display = selected_ticker
name_display   = (str(cred.get("company_name") or "").strip() or
                  selected_label.split("—")[-1].strip())

st.markdown(f"""
<div style="margin-bottom:24px;">
  <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;">
    <span style="font-family:'Syne',sans-serif;font-size:36px;font-weight:800;
                 color:#e8eaf0;letter-spacing:1px;">{ticker_display}</span>
    <span style="font-family:'DM Sans',sans-serif;font-size:16px;
                 color:#4a6a8a;font-weight:300;">{name_display}</span>
    <span style="font-family:'DM Mono',monospace;font-size:12px;
                 background:rgba(99,179,237,0.1);color:#63b3ed;
                 border:1px solid rgba(99,179,237,0.25);border-radius:4px;
                 padding:3px 10px;letter-spacing:1px;">{selected_quarter}</span>
  </div>
</div>
""", unsafe_allow_html=True)

render_kpi_strip(cred, commitments_df)
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

render_alert_banner(alert)
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

st.markdown("### 📋 &nbsp; Guidance Delta Table")
render_guidance_table(commitments_df)
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

st.markdown("### 📈 &nbsp; Hedge Score Trend")
render_hedge_chart(selected_ticker)
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

render_summary_box(summary_text, selected_ticker, selected_quarter)
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)