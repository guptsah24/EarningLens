"""
agent.py
Generates the agentic alert banner for a given ticker / quarter / year.
Uses Ollama (gemma3:12b) when available; falls back to rule-based summary
so the dashboard works on HuggingFace Spaces where Ollama is not running.
"""

from __future__ import annotations
import os
import json
import requests
from supabase_client import fetch_credibility_summary

OLLAMA_URL     = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL   = os.environ.get("OLLAMA_MODEL", "gemma3:12b")
OLLAMA_TIMEOUT = 20  # seconds


def _call_ollama(prompt: str) -> str | None:
    """Call local Ollama. Returns None on any error."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        return None


def _rule_based_alert(ticker: str, quarter: int, year: int, cred: dict) -> dict:
    """
    Deterministic fallback when Ollama is unavailable.
    cred is the dict returned by fetch_credibility_summary.
    Note: credibility_summary has no quarter/year — it's a per-ticker aggregate.
    Column is 'credibility' (not 'credibility_score').
    """
    score      = float(cred.get("credibility", 0.5))
    delivered  = int(cred.get("delivered", 0))
    raised     = int(cred.get("raised", 0))
    missed     = int(cred.get("missed", 0))
    mean_hedge = float(cred.get("mean_hedge", 0.5))
    status     = "WARNING" if (score < 0.6 or missed > 3) else "STABLE"

    headline = (
        f"{ticker}'s management credibility is {'stable' if status == 'STABLE' else 'under pressure'} "
        f"with {delivered} delivered and {raised} raised commitments and {missed} misses "
        f"(credibility score: {score:.2f})."
    )
    if missed == 0:
        detail = "The strongest signal is consistent guidance delivery across all tracked metrics."
    elif missed <= 2:
        detail = (
            f"{missed} commitment(s) missed historically — "
            f"mean hedge score {mean_hedge:.2f} suggests "
            f"{'cautious' if mean_hedge > 0.5 else 'confident'} language overall."
        )
    else:
        detail = (
            f"{missed} commitments missed across tracked history — "
            f"review the guidance table below for which metrics drove the shortfall."
        )

    return {"status": status, "score": round(score, 2), "headline": headline, "detail": detail}


def generate_alert(ticker: str, quarter: int, year: int) -> dict:
    """
    Main entry point called by app.py.
    Returns:
        {
            "status":   "WARNING" | "STABLE",
            "score":    float (0-1),
            "headline": str,
            "detail":   str,
        }

    Note: credibility_summary is a per-ticker aggregate (no quarter/year columns).
    The quarter/year args are kept so callers don't need to change signature.
    """
    cred = fetch_credibility_summary(ticker)  # returns a dict

    prompt = f"""You are a financial analyst assistant. Summarise the overall management credibility 
of {ticker} based on their full guidance history (user is currently viewing Q{quarter} {year}).
Data: credibility={cred.get('credibility', 'N/A')}, 
delivered={cred.get('delivered', 0)}, raised={cred.get('raised', 0)}, 
missed={cred.get('missed', 0)}, total_resolved={cred.get('total_resolved', 0)},
mean_hedge_score={cred.get('mean_hedge', 'N/A')}.
Reply ONLY with a JSON object with keys: status ("WARNING" or "STABLE"), 
score (float 0-1), headline (one sentence), detail (one sentence).
No markdown, no explanation, just the JSON object."""

    llm_output = _call_ollama(prompt)
    if llm_output:
        try:
            clean = llm_output.strip().lstrip("```json").rstrip("```").strip()
            data  = json.loads(clean)
            if all(k in data for k in ("status", "score", "headline", "detail")):
                data["status"] = data["status"].upper()
                if data["status"] not in ("WARNING", "STABLE"):
                    data["status"] = "STABLE"
                data["score"] = min(1.0, max(0.0, float(data["score"])))
                return data
        except Exception:
            pass  # fall through to rule-based

    return _rule_based_alert(ticker, quarter, year, cred)
