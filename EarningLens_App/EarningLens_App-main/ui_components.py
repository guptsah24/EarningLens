"""
ui_components.py — EarningsLens dashboard sections (redesigned)
Dark financial terminal aesthetic. Vivid, readable, spacious.
"""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase_client import fetch_commitments_all_quarters

STATUS_COLOURS = {
    "Delivered": "#22d3a5",
    "Raised":    "#60a5fa",
    "Missed":    "#f87171",
    "Withdrawn": "#6b7280",
    "Pending":   "#94a3b8",
}

STATUS_BG = {
    "Delivered": "rgba(34,211,165,0.12)",
    "Raised":    "rgba(96,165,250,0.12)",
    "Missed":    "rgba(248,113,113,0.12)",
    "Withdrawn": "rgba(107,114,128,0.12)",
    "Pending":   "rgba(148,163,184,0.08)",
}

CHART_PALETTE = ["#60a5fa","#f59e0b","#22d3a5","#f472b6","#a78bfa","#34d399"]


# ── KPI strip ──────────────────────────────────────────────────────────────────
def render_kpi_strip(cred: dict, df: pd.DataFrame) -> None:
    delivered   = int(cred.get("delivered", 0))
    raised      = int(cred.get("raised", 0))
    missed      = int(cred.get("missed", 0))
    total       = int(cred.get("total_resolved", max(delivered + raised + missed, 1)))
    credibility = float(cred.get("credibility", 0))
    mean_hedge  = float(cred.get("mean_hedge", 0))
    n_quarter   = len(df) if not df.empty else 0

    score_color = "#22d3a5" if credibility >= 0.7 else ("#f59e0b" if credibility >= 0.5 else "#f87171")
    hedge_color = "#f87171" if mean_hedge > 0.6 else ("#f59e0b" if mean_hedge > 0.4 else "#22d3a5")
    miss_color  = "#f87171" if missed > 0 else "#22d3a5"

    kpis = [
        ("Credibility",  f"{credibility:.2f}", "lifetime score",      score_color),
        ("Delivered",    str(delivered),        f"of {total} resolved","#22d3a5"),
        ("Missed",       str(missed),           "commitments",         miss_color),
        ("Raised",       str(raised),           "commitments",         "#60a5fa"),
        ("Mean Hedge",   f"{mean_hedge:.2f}",   "lower = confident",   hedge_color),
        ("This Quarter", str(n_quarter),        "commitments",         "#a78bfa"),
    ]

    cols = st.columns(len(kpis))
    for col, (label, value, sub, accent) in zip(cols, kpis):
        with col:
            st.markdown(f"""
<div style="background:#0d1526;border:1px solid rgba(99,179,237,0.14);
            border-top:3px solid {accent};border-radius:10px;
            padding:16px 16px 12px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#3d5a7a;
              letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">{label}</div>
  <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
              color:{accent};line-height:1;">{value}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:#3d5a7a;
              margin-top:4px;">{sub}</div>
</div>""", unsafe_allow_html=True)


# ── Alert Banner ───────────────────────────────────────────────────────────────
def render_alert_banner(alert: dict) -> None:
    status   = alert.get("status", "STABLE")
    score    = alert.get("score", 0.5)
    headline = alert.get("headline", "")
    detail   = alert.get("detail", "")

    is_warn    = status == "WARNING"
    accent     = "#f59e0b" if is_warn else "#22d3a5"
    bg         = "rgba(245,158,11,0.07)" if is_warn else "rgba(34,211,165,0.07)"
    badge_icon = "⚠" if is_warn else "✦"
    badge_txt  = "WARNING" if is_warn else "STABLE"

    st.markdown(f"""
    <div style="
        background:{bg};
        border:1px solid {accent}33;
        border-left:4px solid {accent};
        border-radius:10px;
        padding:22px 28px;
    ">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
        <span style="
            font-family:'DM Mono',monospace;font-size:11px;font-weight:700;
            background:{accent}22;color:{accent};border:1px solid {accent}44;
            border-radius:4px;padding:4px 12px;letter-spacing:2px;">
          {badge_icon} {badge_txt}
        </span>
        <span style="
            font-family:'DM Mono',monospace;font-size:11px;
            background:rgba(255,255,255,0.04);color:#94a3b8;
            border:1px solid rgba(255,255,255,0.08);border-radius:4px;
            padding:4px 12px;letter-spacing:1px;">
          CREDIBILITY · {score:.2f}
        </span>
      </div>
      <div style="font-family:'Syne',sans-serif;font-size:17px;font-weight:700;
                  color:#e8eaf0;margin-bottom:6px;">{headline}</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:14px;
                  color:#7a9ab8;line-height:1.6;">{detail}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Guidance table ─────────────────────────────────────────────────────────────
def render_guidance_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.markdown("""
        <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.1);
                    border-radius:10px;padding:40px;text-align:center;
                    color:#2a4a6a;font-family:'DM Mono',monospace;font-size:13px;">
          NO COMMITMENTS FOUND FOR THIS QUARTER
        </div>""", unsafe_allow_html=True)
        return

    # Drop rows where metric, guided value AND timeframe are all missing/None
    _null = lambda s: s.isna() | (s.astype(str).str.strip().str.lower().isin(["none", "", "nan"]))
    if all(c in df.columns for c in ["Metric", "Guided Value", "Timeframe"]):
        _all_null = _null(df["Metric"]) & _null(df["Guided Value"]) & _null(df["Timeframe"])
        df = df[~_all_null].copy()

    if df.empty:
        st.markdown("""
        <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.1);
                    border-radius:10px;padding:40px;text-align:center;
                    color:#2a4a6a;font-family:'DM Mono',monospace;font-size:13px;">
          NO STRUCTURED COMMITMENTS FOUND FOR THIS QUARTER
        </div>""", unsafe_allow_html=True)
        return

    display_cols = [c for c in
        ["Metric", "Guided Value", "Timeframe", "Status", "Hedge Score", "FLS Label", "Commitment"]
        if c in df.columns]
    display_df = df[display_cols].copy()

    if "Hedge Score" in display_df.columns:
        display_df["Hedge Score"] = display_df["Hedge Score"].apply(
            lambda x: f"{x:.3f}" if pd.notna(x) else "—"
        )
    if "Commitment" in display_df.columns:
        display_df["Commitment"] = display_df["Commitment"].apply(
            lambda x: (x[:100] + "…") if isinstance(x, str) and len(x) > 100 else x
        )

    def _style_row(row):
        styles_list = [""] * len(row)
        status_val  = str(row.get("Status", "")).strip()
        colour      = STATUS_COLOURS.get(status_val, "#94a3b8")
        bg          = STATUS_BG.get(status_val, "")
        for i, col in enumerate(row.index):
            if col == "Status":
                styles_list[i] = f"color:{colour};font-weight:600;font-family:'DM Mono',monospace;font-size:12px;"
            elif col == "Hedge Score":
                styles_list[i] = "font-family:'DM Mono',monospace;color:#a0b4cc;font-size:12px;"
            elif col == "Metric":
                styles_list[i] = "font-weight:600;color:#c8d8ea;"
            elif col == "FLS Label":
                styles_list[i] = "font-family:'DM Mono',monospace;font-size:11px;color:#4a6a8a;"
            else:
                styles_list[i] = "color:#8aa4bc;"
        return styles_list

    styled = (
        display_df.style
        .apply(_style_row, axis=1)
        .set_table_styles([
            {"selector": "table",
             "props": [("background", "#0d1526"), ("border-collapse", "collapse"), ("width","100%")]},
            {"selector": "thead tr th",
             "props": [
                 ("background", "#111e35"), ("color", "#63b3ed"),
                 ("font-family", "'DM Mono', monospace"), ("font-size", "10px"),
                 ("letter-spacing", "1.5px"), ("text-transform", "uppercase"),
                 ("padding", "12px 14px"), ("border-bottom", "2px solid rgba(99,179,237,0.2)"),
             ]},
            {"selector": "tbody tr td",
             "props": [("padding", "11px 14px"), ("border-bottom", "1px solid rgba(255,255,255,0.04)")]},
            {"selector": "tbody tr:hover td",
             "props": [("background", "#14253d !important")]},
        ])
        .hide(axis="index")
    )

    st.dataframe(styled, use_container_width=True, hide_index=True, height=430)

    csv = df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇  Export CSV",
        data=csv,
        file_name=f"guidance_{df.get('ticker', [''])[0] if hasattr(df,'get') else ''}.csv",
        mime="text/csv",
    )


# ── Hedge chart ────────────────────────────────────────────────────────────────
def render_hedge_chart(ticker: str) -> None:
    df = fetch_commitments_all_quarters(ticker)
    if df.empty:
        st.markdown("""
        <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.1);
                    border-radius:10px;padding:60px;text-align:center;
                    color:#2a4a6a;font-family:'DM Mono',monospace;font-size:12px;">
          NO MULTI-QUARTER DATA AVAILABLE
        </div>""", unsafe_allow_html=True)
        return

    df["q_label"] = df.apply(lambda r: f"Q{int(r['quarter'])} {int(r['year'])}", axis=1)
    quarter_order = sorted(df["q_label"].unique(), key=lambda s: (int(s[3:]), int(s[1])))
    top_metrics   = (df.groupby("metric")["hedge_score"].count().nlargest(5).index.tolist())

    fig = go.Figure()
    for i, metric in enumerate(top_metrics):
        m_df = (
            df[df["metric"] == metric]
            .groupby("q_label")["hedge_score"].mean()
            .reindex(quarter_order)
        )
        colour = CHART_PALETTE[i % len(CHART_PALETTE)]
        fig.add_trace(go.Scatter(
            x=m_df.index.tolist(), y=m_df.values.tolist(),
            mode="lines+markers",
            name=metric[:28],
            line=dict(color=colour, width=2.5),
            marker=dict(size=7, color=colour,
                        line=dict(width=1.5, color="#080e1a")),
            hovertemplate=f"<b>{metric[:28]}</b><br>%{{x}}<br>Hedge: %{{y:.3f}}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0d1526",
        margin=dict(l=0, r=0, t=10, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(family="DM Mono", size=10, color="#5d7a99"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            tickangle=-35, tickfont=dict(family="DM Mono", size=10, color="#3d5a7a"),
            gridcolor="rgba(99,179,237,0.06)", linecolor="rgba(99,179,237,0.1)",
        ),
        yaxis=dict(
            title=None, range=[0, 1],
            tickfont=dict(family="DM Mono", size=10, color="#3d5a7a"),
            gridcolor="rgba(99,179,237,0.06)", linecolor="rgba(99,179,237,0.1)",
            tickformat=".2f",
        ),
        height=370,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#111e35", font_family="DM Sans", font_size=12),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        '<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:#1e3a5f;'
        'letter-spacing:1px;margin-top:-10px;">↑ RISING = MORE HEDGING = CREDIBILITY RISK</p>',
        unsafe_allow_html=True,
    )

    # ── LLM explanation of the hedge trend ──────────────────────────────────
    _explain_key = f"hedge_explain_{ticker}"
    if _explain_key not in st.session_state:
        st.session_state[_explain_key] = None

    if st.button("🤖  Explain this trend", key=f"explain_btn_{ticker}"):
        # Build a compact data summary for the prompt
        _rows = []
        for _m in top_metrics:
            _m_df = (
                df[df["metric"] == _m]
                .groupby("q_label")["hedge_score"].mean()
                .reindex(quarter_order)
                .dropna()
            )
            if not _m_df.empty:
                _first, _last = _m_df.iloc[0], _m_df.iloc[-1]
                _trend = "increasing" if _last > _first + 0.05 else ("decreasing" if _last < _first - 0.05 else "stable")
                _rows.append(f"  - {_m}: {_first:.3f} ({_m_df.index[0]}) → {_last:.3f} ({_m_df.index[-1]}) [{_trend}]")
        _data_summary = "\n".join(_rows)

        _prompt = (
            f"You are a financial analyst interpreting hedge score trends for {ticker}.\n"
            f"Hedge scores range 0 to 1: 0 = management is confident and specific, 1 = heavily hedged and vague.\n"
            f"A rising trend means management is becoming less committed and more cautious.\n\n"
            f"Here are the hedge score trends by metric across quarters:\n{_data_summary}\n\n"
            f"In 4-6 sentences, explain what these trends suggest about management credibility and "
            f"how their confidence has evolved over time. Be specific about which metrics are improving "
            f"or deteriorating and what that signals to investors."
        )

        try:
            import os, requests as _req
            _groq_key   = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
            _groq_model = os.environ.get("GROQ_MODEL") or st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            with st.spinner("Analysing trend…"):
                _resp = _req.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {_groq_key}", "Content-Type": "application/json"},
                    json={"model": _groq_model, "messages": [{"role": "user", "content": _prompt}], "max_tokens": 400},
                    timeout=20,
                )
                _resp.raise_for_status()
                st.session_state[_explain_key] = _resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as _e:
            st.session_state[_explain_key] = f"Could not generate explanation: {_e}"

    if st.session_state.get(_explain_key):
        st.markdown(f"""
        <div style="background:#0a1020;border:1px solid rgba(99,179,237,0.1);
                    border-left:4px solid #60a5fa;border-radius:10px;
                    padding:22px 28px;margin-top:12px;">
          <div style="font-family:'DM Mono',monospace;font-size:10px;color:#1a56db;
                      letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">
            🤖 AI TREND ANALYSIS
          </div>
          <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:#b8cce0;
                      line-height:1.8;">{st.session_state[_explain_key]}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Summary box ────────────────────────────────────────────────────────────────
def render_summary_box(summary_text: str, ticker: str, quarter_label: str) -> None:
    st.markdown("### 📝 &nbsp; Plain-English Summary")
    st.markdown(f"""
    <div style="
        background:#0d1526;
        border:1px solid rgba(99,179,237,0.12);
        border-radius:12px;
        padding:28px 32px;
        font-family:'DM Sans',sans-serif;
        font-size:15px;
        line-height:1.8;
        color:#b8cce0;
    ">
        {summary_text}
    </div>
    <p style="font-family:'DM Mono',monospace;font-size:10px;color:#1e3a5f;
              letter-spacing:1px;margin-top:8px;">
      PRE-GENERATED SUMMARY · {ticker} {quarter_label} · SOURCED FROM EARNINGS CALL TRANSCRIPT
    </p>
    """, unsafe_allow_html=True)


# ── Q&A box ────────────────────────────────────────────────────────────────────
def render_qa_box(default_ticker: str) -> None:
    st.markdown("### 💬 &nbsp; Ask the Transcript")

    st.markdown("""
    <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#4a6a8a;
              margin-bottom:16px;">
      Ask anything about this company's guidance history — or any company in the index.
    </p>
    """, unsafe_allow_html=True)

    col_q, col_t = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "Question",
            placeholder='e.g. "What gross margin guidance did they give?" or ask across companies',
            label_visibility="collapsed",
        )
    with col_t:
        ticker_filter = st.text_input(
            "Ticker",
            value=default_ticker,
            label_visibility="collapsed",
        )

    ask = st.button("Ask  →", type="primary")

    if ask and question.strip():
        with st.spinner("Searching commitments…"):
            result = answer_question(question, ticker_filter=ticker_filter.strip() or None)

        st.markdown(f"""
        <div style="
            background:#0d1526;
            border:1px solid rgba(99,179,237,0.18);
            border-left:4px solid #60a5fa;
            border-radius:10px;
            padding:22px 28px;
            margin-top:16px;
            font-family:'DM Sans',sans-serif;
            font-size:15px;
            line-height:1.8;
            color:#b8cce0;
        ">{result['answer']}</div>
        """, unsafe_allow_html=True)

        if result.get("sources"):
            with st.expander(f"  {len(result['sources'])} source commitments retrieved"):
                for src in result["sources"]:
                    sentence = src.get("sentence") or src.get("q_guidance", "")
                    st.markdown(
                        f'<div style="border-bottom:1px solid rgba(99,179,237,0.08);'
                        f'padding:10px 0;font-family:DM Sans,sans-serif;font-size:13px;">'
                        f'<span style="font-family:DM Mono,monospace;font-size:11px;'
                        f'color:#63b3ed;background:rgba(99,179,237,0.1);'
                        f'border-radius:3px;padding:2px 7px;">'
                        f'{src.get("ticker","?")} Q{src.get("quarter","?")} {src.get("year","?")}</span>'
                        f'&nbsp;&nbsp;<span style="color:#4a6a8a;font-style:italic;">'
                        f'{src.get("metric","?")}</span>'
                        f'<br><span style="color:#7a9ab8;">{sentence}</span></div>',
                        unsafe_allow_html=True,
                    )
    elif ask:
        st.warning("Please enter a question.")