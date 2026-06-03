"""
supabase_client.py
All Supabase interactions for EarningsLens — matched to actual table schemas.
Falls back to local parquet files where needed.
"""

import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client


# ── Connection ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment or .streamlit/secrets.toml"
        )
    return create_client(url, key)


# ── Companies ──────────────────────────────────────────────────────────────────
def get_companies() -> pd.DataFrame:
    """
    Returns DataFrame with columns: company_id, ticker, company_name
    Schema: companies(company_id SERIAL PK, ticker TEXT UNIQUE, company_name TEXT)
    """
    sb = get_supabase()
    resp = (
        sb.table("companies")
        .select("company_id, ticker, company_name")
        .order("ticker")
        .execute()
    )
    return pd.DataFrame(resp.data)


# ── Commitments ────────────────────────────────────────────────────────────────
def fetch_commitments(ticker: str, quarter: int, year: int) -> pd.DataFrame:
    """
    Fetch commitments for a given ticker / quarter / year.

    Schema: commitments(
        commitment_id, transcript_id, company_id, quarter, year,
        sentence_text, sentence_hash, metric, value, timeframe,
        hedge_score, fls_label, status, matched_commitment_id
    )

    Returns display-ready DataFrame.
    """
    sb = get_supabase()

    # Resolve company_id from ticker
    co = (
        sb.table("companies")
        .select("company_id")
        .eq("ticker", ticker)
        .execute()
    )
    if not co.data:
        return pd.DataFrame()
    company_id = co.data[0]["company_id"]

    resp = (
        sb.table("commitments")
        .select(
            "metric, value, timeframe, sentence_text, "
            "status, hedge_score, fls_label"
        )
        .eq("company_id", company_id)
        .eq("quarter", quarter)
        .eq("year", year)
        .order("hedge_score", desc=True)
        .limit(20)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if df.empty:
        return df

    # Rename for display
    df.rename(
        columns={
            "metric":       "Metric",
            "value":        "Guided Value",
            "timeframe":    "Timeframe",
            "sentence_text":"Commitment",
            "status":       "Status",
            "hedge_score":  "Hedge Score",
            "fls_label":    "FLS Label",
        },
        inplace=True,
    )
    return df


def fetch_commitments_all_quarters(ticker: str) -> pd.DataFrame:
    """
    Fetch all commitments for a ticker across all quarters for the trend chart.
    Returns columns: metric, quarter, year, hedge_score
    """
    sb = get_supabase()

    co = (
        sb.table("companies")
        .select("company_id")
        .eq("ticker", ticker)
        .execute()
    )
    if not co.data:
        return pd.DataFrame()
    company_id = co.data[0]["company_id"]

    resp = (
        sb.table("commitments")
        .select("metric, quarter, year, hedge_score")
        .eq("company_id", company_id)
        .not_.is_("hedge_score", "null")
        .execute()
    )
    return pd.DataFrame(resp.data)


# ── Summaries ──────────────────────────────────────────────────────────────────
def fetch_summary(ticker: str, quarter: int, year: int) -> str:
    """
    Fetch pre-generated LLM summary.

    Schema: summaries(
        summary_id SERIAL PK, ticker TEXT, company_name TEXT,
        quarter INTEGER, year INTEGER, summary_text TEXT, n_commitments INTEGER
    )

    Falls back to local summaries.parquet.
    """
    try:
        sb = get_supabase()
        resp = (
            sb.table("summaries")
            .select("summary_text, n_commitments")
            .eq("ticker", ticker)
            .eq("quarter", quarter)
            .eq("year", year)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            text = row["summary_text"]
            n    = row.get("n_commitments")
            suffix = f" *(Based on {n} commitments extracted from the transcript.)*" if n else ""
            return text + suffix
    except Exception:
        pass

    # Fallback: local parquet
    try:
        df  = pd.read_parquet("summaries.parquet")
        row = df[
            (df["ticker"] == ticker) &
            (df["quarter"] == quarter) &
            (df["year"] == year)
        ]
        if not row.empty:
            return row.iloc[0]["summary_text"]
    except Exception:
        pass

    return f"No summary available for {ticker} Q{quarter} {year}."


# ── Credibility Summary ────────────────────────────────────────────────────────
def fetch_credibility_summary(ticker: str) -> dict:
    """
    Fetch the credibility summary row for a ticker.

    Schema: credibility_summary(
        id BIGSERIAL PK, ticker TEXT, company_name TEXT,
        delivered INT, raised INT, missed INT, total_resolved INT,
        credibility FLOAT, mean_hedge FLOAT, created_at TIMESTAMPTZ
    )

    Note: this is a per-ticker aggregate (no quarter/year columns).
    Falls back to local credibility_summary.parquet.

    Returns a dict with keys:
        ticker, delivered, raised, missed, total_resolved,
        credibility, mean_hedge
    """
    try:
        sb = get_supabase()
        resp = (
            sb.table("credibility_summary")
            .select(
                "ticker, company_name, delivered, raised, missed, "
                "total_resolved, credibility, mean_hedge"
            )
            .eq("ticker", ticker)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
    except Exception:
        pass

    # Fallback: local parquet
    try:
        df  = pd.read_parquet("credibility_summary.parquet")
        row = df[df["ticker"] == ticker]
        if not row.empty:
            return row.iloc[0].to_dict()
    except Exception:
        pass

    return {
        "ticker": ticker, "delivered": 0, "raised": 0,
        "missed": 0, "total_resolved": 0,
        "credibility": 0.5, "mean_hedge": 0.5,
    }
