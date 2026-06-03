"""
05_upload_transcript.py
EarningsLens — Upload & Analyse a New Earnings Call Transcript

Allows investment bankers to:
  1. Paste or upload a raw earnings call transcript
  2. Get an instant plain-English summary
  3. See extracted commitments in the guidance table format
  4. Ask natural language questions against that transcript (in-session RAG)

Uses the Groq API for extraction + Q&A.
Get a free key at: https://console.groq.com

Add to .streamlit/secrets.toml:
  GROQ_API_KEY = "gsk_..."
  GROQ_MODEL   = "llama-3.3-70b-versatile"   # change this to swap models
"""

from __future__ import annotations
import json
import re
import os
import sys
import streamlit as st
import pandas as pd
from groq import Groq

# ── Auth gate ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import styles, auth_client

st.set_page_config(
    page_title="EarningsLens",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(styles.GLOBAL_CSS, unsafe_allow_html=True)

user = st.session_state.get("user")
if not user:
    st.switch_page("app.py")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(styles.SIDEBAR_HEADER, unsafe_allow_html=True)
    st.markdown(
        '<p style="font-family:\'DM Mono\',monospace;font-size:10px;'
        'color:#1e3a5f;letter-spacing:1px;">UPLOAD & ANALYSE</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    user_meta = getattr(user, "user_metadata", {}) or {}
    display_name = (
        user_meta.get("full_name") or user_meta.get("name")
        or getattr(user, "email", "") or ""
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

    st.markdown("---")
    st.markdown(
        '<p style="font-family:\'DM Mono\',monospace;font-size:10px;'
        'color:#2a4a6a;letter-spacing:1px;">NAVIGATE</p>',
        unsafe_allow_html=True,
    )
    if st.button("📊  Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ── Groq API config ────────────────────────────────────────────────────────────
GROQ_API_KEY = (
    os.environ.get("GROQ_API_KEY")
    or st.secrets.get("GROQ_API_KEY", "")
)

GROQ_MODEL = (
    os.environ.get("GROQ_MODEL")
    or st.secrets.get("GROQ_MODEL", "llama-3.3-70b-versatile")
)


def _call_groq(system: str, user_msg: str, max_tokens: int = 2000) -> str:
    """Call Groq API. Model is set via GROQ_MODEL in secrets.toml."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set.\n\n"
            "1. Get a free key at https://console.groq.com\n"
            "2. Add it to .streamlit/secrets.toml:\n\n"
            "   GROQ_API_KEY = 'gsk_...'\n\n"
            "Optionally set a model (default: llama-3.3-70b-versatile):\n"
            "   GROQ_MODEL = 'llama-3.3-70b-versatile'"
        )
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()


# ── Hedge Scorer — faithful port of EarningsLens Stage 5 ──────────────────────
#
# Stage 5 uses a two-signal architecture:
#
#   Signal 1 — Loughran-McDonald (LM) lexical hedge score  (weight: 0.65)
#     Proportion of sentence tokens that appear in the LM Uncertainty or
#     Constraining word categories, extended with a custom financial phrase
#     list.  Raw density is clipped at LM_CLIP=0.20 then normalised to [0,1].
#
#   Signal 2 — Tone polarity score                         (weight: 0.35)
#     In the pipeline this is finbert-tone (GPU model).  Here we approximate
#     it with a lightweight lexical tone classifier using positive/negative
#     financial word lists — same mapping logic as the pipeline:
#       positive tone + high confidence → near 0.0
#       neutral                         → 0.5
#       negative tone + high confidence → near 1.0
#
#   Final: hedge_score = 0.65 × lm_score + 0.35 × tone_score   (clipped 0–1)
#
# The LM word set covers ~86k financial words.  We ship a compact subset of
# the most common LM Uncertainty / Constraining words found in earnings calls,
# extended with the same CUSTOM_HEDGE_PHRASES list used in the pipeline.

import re as _re

# ── LM Uncertainty / Constraining core words (earnings-call-relevant subset) ──
# Source: Loughran-McDonald Master Dictionary — Uncertainty + Constraining cols
_LM_HEDGE_WORDS = {
    # Uncertainty category (LM)
    "approximate", "approximately", "contingencies", "contingency", "contingent",
    "depend", "depended", "dependent", "depending", "depends",
    "doubt", "doubtful", "doubts",
    "estimate", "estimated", "estimates", "estimating",
    "indefinite", "indefinitely", "indefiniteness",
    "intend", "intended", "intending", "intends",
    "likely", "likelihood",
    "may", "might",
    "nearly",
    "possible", "possibly", "possibility",
    "potential", "potentially",
    "roughly",
    "subject",
    "uncertain", "uncertainties", "uncertainty",
    "unclear",
    "unpredictable",
    "variable",
    # Constraining category (LM)
    "cannot", "can't",
    "constraint", "constrained", "constraining",
    "dependent",
    "inhibit", "inhibited",
    "limit", "limited", "limiting", "limitation",
    "must",
    "obligation", "obligate", "obligated",
    "prohibit", "prohibited",
    "require", "required", "requires", "requiring",
    "restrict", "restricted", "restricting", "restriction",
    "shall",
}

# ── Custom hedge phrases — same set as Stage 5 pipeline ───────────────────────
_CUSTOM_HEDGE_PHRASES = {
    # Modal verbs
    "may", "might", "could", "would", "should",
    # Forward-looking verbs with uncertainty
    "expect", "expects", "expected", "expecting",
    "believe", "believes", "believed",
    "estimate", "estimates", "estimated",
    "forecast", "forecasts", "forecasted",
    "project", "projects", "projected",
    "intend", "intends", "intended",
    # Qualifiers
    "approximately", "roughly", "around", "about",
    "potential", "potentially",
    "possible", "possibly",
    "likely", "unlikely",
    "tend", "tends",
    "assume", "assumes", "assumed", "assuming",
    # Conditional
    "subject to", "contingent", "dependent",
    "provided that", "assuming that",
    # Range language
    "range", "between", "up to", "at least",
    "more than", "less than", "above", "below",
    # Softeners
    "somewhat", "slightly", "modestly", "broadly",
    "generally", "typically", "usually",
}

# Combined extended hedge word set (same as hedge_words_extended in notebook)
_HEDGE_WORDS_EXTENDED = _LM_HEDGE_WORDS | _CUSTOM_HEDGE_PHRASES

# Tokeniser — same regex as Stage 5: splits on whitespace and punctuation
_TOKEN_RE = _re.compile(r"[a-zA-Z']+")

# LM density clip — same value as Stage 5 (LM_CLIP = 0.20)
_LM_CLIP = 0.20

# ── Signal 1: LM score (always local) ─────────────────────────────────────────

def _lm_score(sentence: str) -> float:
    """
    Loughran-McDonald lexical hedge score.
    Proportion of tokens in the extended LM hedge set,
    normalised by LM_CLIP=0.20 and clipped to [0, 1].
    Matches Stage 5 lm_hedge_score() exactly.
    """
    tokens = _TOKEN_RE.findall(sentence.lower())
    if not tokens:
        return 0.0
    hedge_count = sum(1 for t in tokens if t in _HEDGE_WORDS_EXTENDED)
    raw_density = hedge_count / len(tokens)
    return min(raw_density / _LM_CLIP, 1.0)


# ── Signal 2: finbert-tone via HuggingFace Space ───────────────────────────────
# Real finbert-tone hosted at: https://huggingface.co/spaces/Sidsuresh/EarningLens_FinBERT
# Falls back to lexical approximation if the Space is unreachable.

import urllib.request as _urllib_request

_FINBERT_API_URL = "https://sidsuresh-earninglens-finbert.hf.space/score"
_FINBERT_TIMEOUT = 60   # seconds — generous for CPU cold start on free tier


def _tone_scores_from_api(sentences: list[str]) -> list[float] | None:
    """
    POST sentences to the HF Space finbert-tone API.
    Returns tone_scores aligned with input, or None on any failure.
    The API applies the same tone_to_hedge() mapping as Stage 5:
        positive + high confidence → near 0.0
        neutral                    → 0.5
        negative + high confidence → near 1.0
    """
    import json as _json
    payload = _json.dumps({"sentences": sentences}).encode("utf-8")
    req = _urllib_request.Request(
        _FINBERT_API_URL,
        data    = payload,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    try:
        with _urllib_request.urlopen(req, timeout=_FINBERT_TIMEOUT) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            return data["tone_scores"]
    except Exception:
        return None


# ── Lexical fallback (used when HF Space is unreachable) ──────────────────────
_TONE_POSITIVE = {
    "will", "confident", "confidence", "strong", "strength",
    "deliver", "delivered", "delivering", "achieve", "achieved", "achieving",
    "commit", "committed", "committing", "commitment",
    "grow", "growth", "accelerate", "acceleration",
    "record", "exceed", "exceeded", "exceeding", "outperform",
    "pleased", "excited", "proud",
    "improving", "improved", "improvement",
    "solid", "robust",
}
_TONE_NEGATIVE = {
    "challenging", "challenge", "challenges",
    "difficult", "difficulty", "difficulties",
    "headwind", "headwinds", "pressure", "pressures",
    "decline", "declining", "declined",
    "weakness", "weak", "weaker",
    "uncertain", "uncertainty", "uncertainties",
    "risk", "risks", "risky", "volatile", "volatility",
    "concern", "concerns", "concerned",
    "disappoint", "disappointed", "disappointing",
    "miss", "missed",
    "deteriorate", "deteriorating", "deterioration",
    "adverse", "adversely", "unfavorable", "unfavourable",
}


def _tone_score_lexical(sentence: str) -> float:
    """Lexical fallback — same tone_to_hedge() mapping as the API."""
    text   = sentence.lower()
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return 0.5
    pos = sum(1 for t in tokens if t in _TONE_POSITIVE)
    neg = sum(1 for t in tokens if t in _TONE_NEGATIVE)
    if "on track" in text or "on pace" in text or "ahead of" in text:
        pos += 1
    total = pos + neg
    if total == 0:
        return 0.5
    if pos > neg:
        return max(0.0, 1.0 - pos / total)
    return min(1.0, neg / total)


# Blend weights — same as Stage 5 configuration cell
_LM_BLEND   = 0.65
_TONE_BLEND = 0.35


def compute_hedge_scores_batch(sentences: list[str]) -> tuple[list[float], bool]:
    """
    Compute hedge scores for a batch using the Stage 5 two-signal architecture:
        hedge_score = 0.65 × lm_score + 0.35 × tone_score

    Signal 1 (LM, 0.65):   always local — instant.
    Signal 2 (Tone, 0.35):  tries HF Space finbert-tone API first,
                            falls back to lexical approximation on failure.

    Returns: (scores list, used_api bool)
    """
    if not sentences:
        return [], False

    lm_scores   = [_lm_score(s) for s in sentences]
    tone_scores = _tone_scores_from_api(sentences)
    used_api    = tone_scores is not None

    if not used_api:
        tone_scores = [_tone_score_lexical(s) for s in sentences]

    results = [
        round(float(max(0.0, min(1.0, _LM_BLEND * lm + _TONE_BLEND * tone))), 3)
        for lm, tone in zip(lm_scores, tone_scores)
    ]
    return results, used_api


def compute_hedge_score(sentence: str) -> float:
    """Single-sentence convenience wrapper."""
    scores, _ = compute_hedge_scores_batch([sentence])
    return scores[0]


# ── Extraction helpers ─────────────────────────────────────────────────────────
EXTRACT_SYSTEM = """You are a financial analyst extracting forward-looking commitments
from earnings call transcripts. Extract every forward guidance statement made by management.

Reply ONLY with a JSON array (no markdown, no explanation). Each element:
{
  "metric":    string  — what is being guided (e.g. "Revenue", "Gross Margin"),
  "value":     string  — the guided value or range (e.g. "$90-92B", ">45%"),
  "timeframe": string  — when (e.g. "Q2 2025", "FY 2025", "next quarter"),
  "sentence":  string  — the exact sentence from the transcript,
  "fls_label": string  — one of: "Quantitative", "Qualitative", "Directional"
}

Do NOT include a hedge_score field — that is computed separately.

Extract up to 20 commitments. If fewer exist, return what you find."""

SUMMARY_SYSTEM = """You are a financial analyst writing plain-English summaries
of earnings call transcripts for investors of all experience levels.

Write 4–6 sentences covering:
1. What quarter/period this covers and the company
2. Key financial commitments made (revenue, margins, etc.)
3. Management's overall tone — confident or cautious?
4. Any notable risks or concerns mentioned
5. The most important single takeaway

Avoid jargon. Write for a smart non-specialist. Be direct and specific."""

QA_SYSTEM = """You are a financial analyst assistant. Answer questions about
earnings call transcripts using ONLY the provided transcript text and
extracted commitments. Be concise (3–5 sentences). If the answer
isn't in the sources, say so clearly. Do not speculate."""


def extract_commitments(transcript: str) -> tuple[list[dict], bool]:
    """
    Extract commitments from transcript and compute hedge scores.
    Returns (commitments, used_finbert_api).
    Hedge scores use the Stage 5 two-signal method:
        - Signal 1 (LM, 0.65): always local
        - Signal 2 (Tone, 0.35): real finbert-tone via HF Space, lexical fallback
    """
    raw = _call_groq(EXTRACT_SYSTEM, f"Transcript:\n\n{transcript[:15000]}", max_tokens=3000)
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        items = json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", clean, re.DOTALL)
        if m:
            items = json.loads(m.group())
        else:
            items = []

    if not items:
        return [], False

    # Batch hedge scoring — one API call for all sentences
    sentences = [item.get("sentence", "") for item in items]
    scores, used_api = compute_hedge_scores_batch(sentences)
    for item, score in zip(items, scores):
        item["hedge_score"] = score

    return items, used_api


def generate_summary(transcript: str, ticker: str, quarter: str) -> str:
    prompt = f"Company: {ticker or 'Unknown'}\nPeriod: {quarter or 'Unknown'}\n\nTranscript:\n\n{transcript[:12000]}"
    return _call_groq(SUMMARY_SYSTEM, prompt, max_tokens=600)


# ── In-session RAG for uploaded transcripts ──────────────────────────
#
#  Proper RAG replacing old context-stuffing:
#    1. Chunk transcript into overlapping windows
#    2. Embed each chunk with all-MiniLM-L6-v2 (same model as main pipeline)
#    3. Build an in-memory FAISS index (discarded after session)
#    4. Per question: embed query, retrieve top-K chunks, generate with Groq
#
#  Index is keyed on transcript hash so it is only rebuilt when transcript changes.

import hashlib as _hashlib

SS_RAG_INDEX  = "ut_rag_index"
SS_RAG_CHUNKS = "ut_rag_chunks"
SS_RAG_HASH   = "ut_rag_hash"

RAG_CHUNK_SIZE    = 400   # characters per chunk
RAG_CHUNK_OVERLAP = 80    # overlap between consecutive chunks
RAG_TOP_K         = 5     # chunks retrieved per question


def _chunk_transcript(text: str) -> list[str]:
    """Split transcript into overlapping chunks, snapping to sentence boundaries."""
    chunks = []
    start  = 0
    length = len(text)
    while start < length:
        end = min(start + RAG_CHUNK_SIZE, length)
        # Try to snap to a sentence boundary, but only search forward from midpoint
        if end < length:
            search_from = start + RAG_CHUNK_SIZE // 2
            boundary = text.rfind(". ", search_from, end)
            if boundary != -1:
                end = boundary + 2
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        # Advance must always move forward by at least 1 character
        next_start = end - RAG_CHUNK_OVERLAP
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return chunks


def _get_embedder():
    """Load all-MiniLM-L6-v2 -- same model used by the main FAISS pipeline."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def build_rag_index(transcript: str) -> bool:
    """
    Chunk the transcript, embed all chunks, and store a FAISS flat index
    in st.session_state. Returns True if index was built, False on failure.
    The index is only rebuilt when the transcript changes (hash check).
    """
    text_hash = _hashlib.md5(transcript.encode()).hexdigest()
    if st.session_state.get(SS_RAG_HASH) == text_hash:
        return True  # already indexed for this transcript

    embedder = _get_embedder()
    if embedder is None:
        return False

    try:
        import faiss  # type: ignore
        import numpy as np
    except ImportError:
        return False

    chunks = _chunk_transcript(transcript)
    if not chunks:
        return False

    embeddings = embedder.encode(chunks, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(embeddings)  # cosine similarity via inner product

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product = cosine on normalised vecs
    index.add(embeddings)

    st.session_state[SS_RAG_INDEX]  = index
    st.session_state[SS_RAG_CHUNKS] = chunks
    st.session_state[SS_RAG_HASH]   = text_hash
    return True


def _retrieve_chunks(question: str) -> list[str]:
    """Embed the question and return the top-K most relevant transcript chunks."""
    index  = st.session_state.get(SS_RAG_INDEX)
    chunks = st.session_state.get(SS_RAG_CHUNKS, [])
    if index is None or not chunks:
        return []

    embedder = _get_embedder()
    if embedder is None:
        return []

    import numpy as np
    import faiss  # type: ignore
    q_vec = embedder.encode([question]).astype("float32")
    faiss.normalize_L2(q_vec)
    _, I = index.search(q_vec, min(RAG_TOP_K, len(chunks)))
    return [chunks[i] for i in I[0] if i < len(chunks)]


def ask_transcript(question: str, transcript: str, commitments: list[dict]) -> str:
    """
    RAG-based Q&A over the uploaded transcript.
    Retrieves top-K chunks via FAISS cosine similarity, then generates
    an answer with Groq. Falls back to context-stuffing if FAISS or
    sentence-transformers are unavailable.
    """
    retrieved = _retrieve_chunks(question)

    if retrieved:
        rag_context = "\n\n---\n\n".join(retrieved)
        commitment_text = "\n".join(
            f"[{c.get('metric','?')} | {c.get('timeframe','?')}] {c.get('sentence','')}"
            for c in commitments[:15]
        )
        context = (
            f"RETRIEVED TRANSCRIPT CHUNKS (most relevant to question):\n\n{rag_context}\n\n"
            f"EXTRACTED COMMITMENTS:\n{commitment_text}"
        )
    else:
        # Fallback: plain context-stuffing (FAISS/sentence-transformers unavailable)
        commitment_text = "\n".join(
            f"[{c.get('metric','?')} | {c.get('timeframe','?')}] {c.get('sentence','')}"
            for c in commitments[:15]
        )
        context = f"TRANSCRIPT EXCERPT:\n{transcript[:6000]}\n\nEXTRACTED COMMITMENTS:\n{commitment_text}"

    return _call_groq(QA_SYSTEM, f"Context:\n{context}\n\nQuestion: {question}", max_tokens=500)


# ── Status colours ─────────────────────────────────────────────────────────────
STATUS_COLOURS = {
    "Delivered": "#22d3a5",
    "Raised":    "#60a5fa",
    "Missed":    "#f87171",
    "Withdrawn": "#6b7280",
    "Pending":   "#94a3b8",
}

def _hedge_colour(score: float) -> str:
    if score <= 0.33:  return "#22d3a5"
    if score <= 0.66:  return "#f59e0b"
    return "#f87171"


# ── Session state keys ─────────────────────────────────────────────────────────
SS_TRANSCRIPT   = "ut_transcript"
SS_TICKER       = "ut_ticker"
SS_QUARTER      = "ut_quarter"
SS_COMMITMENTS  = "ut_commitments"
SS_SUMMARY      = "ut_summary"
SS_QA_HISTORY   = "ut_qa_history"

for key, default in [
    (SS_TRANSCRIPT,  ""),
    (SS_TICKER,      ""),
    (SS_QUARTER,     ""),
    (SS_COMMITMENTS, []),
    (SS_SUMMARY,     ""),
    (SS_QA_HISTORY,  []),
    (SS_RAG_INDEX,   None),
    (SS_RAG_CHUNKS,  []),
    (SS_RAG_HASH,    ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
# ── Hero intro
st.markdown("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:600;
              color:#1a56db;letter-spacing:3px;text-transform:uppercase;
              margin-bottom:12px;">🔭 EarningsLens</div>
  <h1 style="font-family:'Syne',sans-serif;font-size:38px;font-weight:800;
             color:#e8eaf0;line-height:1.15;margin:0 0 14px;">
    What did management<br><span style="color:#63b3ed;">actually commit to?</span>
  </h1>
  <p style="font-family:'DM Sans',sans-serif;font-size:16px;color:#4a6a8a;
            line-height:1.7;max-width:680px;margin:0;">
    EarningsLens reads earnings call transcripts and extracts every forward-looking
    commitment management makes — revenue targets, margin guidance, growth pledges —
    scores how confident they sound, and tracks whether they actually delivered across quarters.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Audience cards (3 columns)
_c1, _c2, _c3 = st.columns(3)
with _c1:
    st.markdown("""
    <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.14);
                border-top:3px solid #a78bfa;border-radius:10px;padding:20px;height:100%;">
      <div style="font-size:22px;margin-bottom:8px;">🔰</div>
      <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
                  color:#e8eaf0;margin-bottom:6px;">Beginner Investors</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#4a6a8a;line-height:1.6;">
        Plain-English summaries of every call. No financial jargon.
        Ask any question and get a straight answer from the transcript.
      </div>
    </div>
    """, unsafe_allow_html=True)
with _c2:
    st.markdown("""
    <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.14);
                border-top:3px solid #22d3a5;border-radius:10px;padding:20px;height:100%;">
      <div style="font-size:22px;margin-bottom:8px;">📊</div>
      <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
                  color:#e8eaf0;margin-bottom:6px;">Brokers &amp; Analysts</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#4a6a8a;line-height:1.6;">
        Structured guidance delta table with Raise, Miss, and Withdrawal flags.
        Export to CSV for your own models.
      </div>
    </div>
    """, unsafe_allow_html=True)
with _c3:
    st.markdown("""
    <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.14);
                border-top:3px solid #60a5fa;border-radius:10px;padding:20px;height:100%;">
      <div style="font-size:22px;margin-bottom:8px;">🧠</div>
      <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
                  color:#e8eaf0;margin-bottom:6px;">Experienced Investors</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#4a6a8a;line-height:1.6;">
        Quantified credibility trend charts and automatic agentic alerts
        when management’s specificity drops across quarters.
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── What you get + Dashboard callout (2 columns)
_d1, _d2 = st.columns(2)
with _d1:
    st.markdown("""
    <div style="background:#0a1020;border:1px solid rgba(99,179,237,0.08);
                border-radius:10px;padding:20px 24px;">
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:#1e3a5f;
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;">
        What you get from each transcript
      </div>
      <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#4a6a8a;line-height:2;">
        <span style="color:#22d3a5;">✓</span>&nbsp; Forward guidance commitments extracted &amp; structured<br>
        <span style="color:#22d3a5;">✓</span>&nbsp; Hedge score per commitment (0 = confident, 1 = vague)<br>
        <span style="color:#22d3a5;">✓</span>&nbsp; Plain-English summary of the full call<br>
        <span style="color:#22d3a5;">✓</span>&nbsp; Interactive Q&amp;A — ask anything about the transcript
      </div>
    </div>
    """, unsafe_allow_html=True)
with _d2:
    st.markdown("""
    <div style="background:#0a1020;border:1px solid rgba(26,86,219,0.25);
                border-left:3px solid #1a56db;border-radius:10px;padding:20px 24px;">
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:#1a56db;
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">
        📊 Also available: S&amp;P 500 Dashboard
      </div>
      <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:#b8cce0;
                  line-height:1.7;margin-bottom:12px;">
        Want to explore pre-analysed data? The <strong style="color:#63b3ed;">Dashboard</strong>
        covers <strong style="color:#e8eaf0;">531 S&amp;P 500 companies</strong> with
        guidance tracking from <strong style="color:#e8eaf0;">Q1 2023 through Q1 2025</strong>.
        Compare credibility trends, view hedge score histories, and run Q&amp;A
        against any company’s call — no upload required.
      </div>
      <div style="font-family:'DM Mono',monospace;font-size:11px;color:#3d5a7a;
                  letter-spacing:1px;">USE THE SIDEBAR → DASHBOARD</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#2a4a6a;
    letter-spacing:2px;text-transform:uppercase;line-height:1.8;">
    
    ↓ &nbsp; Paste or upload a transcript below to get started<br>
    
    <span style="font-size:10px;color:#3d5a7a;">
    You can get transcripts from:
    <a href="https://seekingalpha.com/earnings/earnings-call-transcripts"
       target="_blank"
       style="color:#63b3ed;text-decoration:none;">
       Here (Seeking Alpha)
    </a>
    </span>
    
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

if not GROQ_API_KEY:
    st.error(
        "⚠️ **GROQ_API_KEY not found.**\n\n"
        "1. Get a **free** key at [console.groq.com](https://console.groq.com)\n"
        "2. Add it to `.streamlit/secrets.toml`:\n\n"
        "```toml\nGROQ_API_KEY = 'gsk_...'\n```"
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — INPUT
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 1 · Load Transcript")

col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    ticker_input = st.text_input(
        "Ticker / Company name",
        value=st.session_state[SS_TICKER],
        placeholder="e.g. AAPL",
    )
with col_meta2:
    quarter_input = st.text_input(
        "Quarter / Period",
        value=st.session_state[SS_QUARTER],
        placeholder="e.g. Q2 2025",
    )

tab_paste, tab_upload = st.tabs(["📋  Paste text", "📁  Upload .txt / .pdf"])

pasted = ""

with tab_paste:
    pasted = st.text_area(
        "Paste transcript here",
        height=260,
        placeholder="Paste the full earnings call transcript…",
        label_visibility="collapsed",
    )

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload transcript",
        type=["txt", "pdf"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        if uploaded_file.name.endswith(".pdf"):
            try:
                import io
                import pdfplumber  # type: ignore
                pdf_bytes = io.BytesIO(uploaded_file.read())
                with pdfplumber.open(pdf_bytes) as pdf:
                    pasted = "\n\n".join(
                        p.extract_text() or "" for p in pdf.pages
                    )
                if pasted.strip():
                    st.success(f"Extracted text from {len(pasted):,} characters of PDF.")
                else:
                    st.warning(
                        "PDF opened but no text extracted — it may be a scanned image. "
                        "Try pasting the transcript text directly instead."
                    )
            except Exception as e:
                import subprocess
                pip_out = subprocess.run(
                    [sys.executable, "-m", "pip", "show", "pdfplumber"],
                    capture_output=True, text=True
                ).stdout or "pdfplumber not found in this environment"
                st.error(
                    f"PDF extraction failed: {e}\n\n"
                    f"**Python executable:** `{sys.executable}`\n\n"
                    f"**pdfplumber status:**\n```\n{pip_out}\n```\n\n"
                    f"Run this to install into the correct environment:\n"
                    f"```\n{sys.executable} -m pip install pdfplumber\n```"
                )
                pasted = ""
        else:
            pasted = uploaded_file.read().decode("utf-8", errors="replace")
            st.success(f"Loaded {len(pasted):,} characters.")

# Resolve active transcript text
active_transcript = pasted.strip() if pasted and pasted.strip() else st.session_state[SS_TRANSCRIPT]

char_count = len(active_transcript)
if char_count > 0:
    st.caption(f"Transcript loaded · {char_count:,} characters (~{char_count // 4:,} tokens)")

analyse_btn = st.button(
    "⚡  Analyse Transcript",
    type="primary",
    disabled=char_count < 100,
    help="Minimum 100 characters required",
)

SS_FINBERT_USED = "ut_finbert_used"
if SS_FINBERT_USED not in st.session_state:
    st.session_state[SS_FINBERT_USED] = False

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS — runs when button pressed
# ══════════════════════════════════════════════════════════════════════════════
if analyse_btn and active_transcript:
    st.session_state[SS_TRANSCRIPT] = active_transcript
    st.session_state[SS_TICKER]     = ticker_input.strip().upper()
    st.session_state[SS_QUARTER]    = quarter_input.strip()
    st.session_state[SS_QA_HISTORY] = []

    with st.spinner("Extracting commitments…"):
        try:
            commitments, used_api = extract_commitments(active_transcript)
            st.session_state[SS_COMMITMENTS]  = commitments
            st.session_state[SS_FINBERT_USED] = used_api
        except Exception as e:
            st.error(f"Commitment extraction failed: {e}")
            commitments = []
            st.session_state[SS_FINBERT_USED] = False

    with st.spinner("Generating summary…"):
        try:
            summary = generate_summary(
                active_transcript,
                st.session_state[SS_TICKER],
                st.session_state[SS_QUARTER],
            )
            st.session_state[SS_SUMMARY] = summary
        except Exception as e:
            st.error(f"Summary generation failed: {e}")
            st.session_state[SS_SUMMARY] = "Summary unavailable."

    with st.spinner("Building RAG index…"):
        rag_built = build_rag_index(active_transcript)
        if not rag_built:
            st.caption(
                "⚠️ RAG index unavailable (faiss or sentence-transformers not installed). "
                "Q&A will use truncated context instead."
            )

    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTS — shown after analysis
# ══════════════════════════════════════════════════════════════════════════════
commitments  = st.session_state[SS_COMMITMENTS]
summary      = st.session_state[SS_SUMMARY]
transcript   = st.session_state[SS_TRANSCRIPT]
finbert_used = st.session_state.get(SS_FINBERT_USED, False)

if not commitments and not summary:
    st.markdown("""
    <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.1);
                border-radius:10px;padding:60px;text-align:center;
                color:#2a4a6a;font-family:'DM Mono',monospace;font-size:13px;
                margin-top:32px;">
      PASTE A TRANSCRIPT ABOVE AND CLICK ANALYSE TO BEGIN
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Header badge
ticker_disp  = st.session_state[SS_TICKER] or "UNKNOWN"
quarter_disp = st.session_state[SS_QUARTER] or "Unknown period"

st.markdown(f"""
<div style="margin:28px 0 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
  <span style="font-family:'Syne',sans-serif;font-size:24px;font-weight:800;color:#e8eaf0;">
    {ticker_disp}
  </span>
  <span style="font-family:'DM Mono',monospace;font-size:12px;
               background:rgba(99,179,237,0.1);color:#63b3ed;
               border:1px solid rgba(99,179,237,0.25);border-radius:4px;
               padding:3px 10px;letter-spacing:1px;">{quarter_disp}</span>
  <span style="font-family:'DM Mono',monospace;font-size:11px;color:#3d5a7a;">
    {len(commitments)} commitments extracted
  </span>
</div>
""", unsafe_allow_html=True)


# ── Section A: KPI strip ───────────────────────────────────────────────────────
if commitments:
    n_quant = sum(1 for c in commitments if c.get("fls_label") == "Quantitative")
    n_qual  = sum(1 for c in commitments if c.get("fls_label") == "Qualitative")
    n_dir   = sum(1 for c in commitments if c.get("fls_label") == "Directional")
    scores  = [c.get("hedge_score", 0.5) for c in commitments if c.get("hedge_score") is not None]
    mean_h  = sum(scores) / len(scores) if scores else 0.5
    hedge_col = "#f87171" if mean_h > 0.6 else ("#f59e0b" if mean_h > 0.4 else "#22d3a5")

    kpis = [
        ("Commitments",   str(len(commitments)), "extracted",           "#a78bfa"),
        ("Quantitative",  str(n_quant),          "with hard numbers",   "#22d3a5"),
        ("Qualitative",   str(n_qual),           "directional guidance","#60a5fa"),
        ("Directional",   str(n_dir),            "trend statements",    "#f59e0b"),
        ("Mean Hedge",    f"{mean_h:.2f}",       "lower = confident",   hedge_col),
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

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)


# ── Section B: Plain-English Summary ──────────────────────────────────────────
st.markdown("### 📝 &nbsp; Plain-English Summary")
st.markdown(f"""
<div style="background:#0d1526;border:1px solid rgba(99,179,237,0.12);
            border-radius:12px;padding:28px 32px;
            font-family:'DM Sans',sans-serif;font-size:15px;
            line-height:1.8;color:#b8cce0;">
  {summary}
</div>
<p style="font-family:'DM Mono',monospace;font-size:10px;color:#1e3a5f;
          letter-spacing:1px;margin-top:8px;">
  AI-GENERATED SUMMARY · {ticker_disp} {quarter_disp}
</p>
""", unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)


# ── Section C: Commitments table ──────────────────────────────────────────────
st.markdown("### 📋 &nbsp; Extracted Commitments")

if commitments:
    df = pd.DataFrame(commitments)

    for col in ["metric", "value", "timeframe", "hedge_score", "fls_label", "sentence"]:
        if col not in df.columns:
            df[col] = None

    df["hedge_score"] = pd.to_numeric(df["hedge_score"], errors="coerce").fillna(0.5)
    df = df.sort_values("hedge_score", ascending=False)
    df["status"] = "Pending"

    disp = df.rename(columns={
        "metric":      "Metric",
        "value":       "Guided Value",
        "timeframe":   "Timeframe",
        "status":      "Status",
        "hedge_score": "Hedge Score",
        "fls_label":   "FLS Label",
        "sentence":    "Commitment",
    })

    show_cols = ["Metric", "Guided Value", "Timeframe", "Status", "Hedge Score", "FLS Label", "Commitment"]
    show_cols = [c for c in show_cols if c in disp.columns]
    disp = disp[show_cols].copy()
    disp["Hedge Score"] = disp["Hedge Score"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    disp["Commitment"] = disp["Commitment"].apply(
        lambda x: (x[:100] + "…") if isinstance(x, str) and len(x) > 100 else (x or "")
    )

    st.dataframe(disp, use_container_width=True, hide_index=True, height=420)

    csv = disp.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇  Export Commitments CSV",
        data=csv,
        file_name=f"commitments_{ticker_disp}_{quarter_disp.replace(' ','_')}.csv",
        mime="text/csv",
    )
else:
    st.markdown("""
    <div style="background:#0d1526;border:1px solid rgba(99,179,237,0.1);
                border-radius:10px;padding:40px;text-align:center;
                color:#2a4a6a;font-family:'DM Mono',monospace;font-size:13px;">
      NO COMMITMENTS EXTRACTED
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ── Section D: Hedge score bar chart ──────────────────────────────────────────
if commitments:
    st.markdown("### 📊 &nbsp; Hedge Score by Metric")
    import plotly.graph_objects as go

    df_chart = pd.DataFrame(commitments)
    if "metric" in df_chart.columns and "hedge_score" in df_chart.columns:
        df_chart["hedge_score"] = pd.to_numeric(df_chart["hedge_score"], errors="coerce").fillna(0.5)
        df_chart = df_chart.groupby("metric")["hedge_score"].mean().reset_index()
        df_chart = df_chart.sort_values("hedge_score", ascending=True).head(15)
        df_chart["colour"] = df_chart["hedge_score"].apply(_hedge_colour)

        fig = go.Figure(go.Bar(
            x=df_chart["hedge_score"],
            y=df_chart["metric"],
            orientation="h",
            marker_color=df_chart["colour"].tolist(),
            hovertemplate="<b>%{y}</b><br>Hedge Score: %{x:.3f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0d1526",
            margin=dict(l=0, r=20, t=10, b=10),
            xaxis=dict(
                range=[0, 1],
                tickfont=dict(family="DM Mono", size=10, color="#3d5a7a"),
                gridcolor="rgba(99,179,237,0.06)",
            ),
            yaxis=dict(
                tickfont=dict(family="DM Sans", size=12, color="#b8cce0"),
                automargin=True,
            ),
            height=max(250, len(df_chart) * 36),
            hovermode="y unified",
            hoverlabel=dict(bgcolor="#111e35", font_family="DM Sans", font_size=12),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            '<p style="font-family:\'DM Mono\',monospace;font-size:10px;color:#1e3a5f;'
            'letter-spacing:1px;margin-top:-10px;">GREEN = CONFIDENT · RED = HEDGED</p>',
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ── Section E: Q&A ────────────────────────────────────────────────────────────
st.markdown("### 💬 &nbsp; Ask the Transcript")
st.markdown("""
<p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#4a6a8a;margin-bottom:16px;">
  Ask anything about this earnings call — guidance targets, tone, risks, comparisons.
</p>
""", unsafe_allow_html=True)

# Show Q&A history
for qa in st.session_state[SS_QA_HISTORY]:
    st.markdown(f"""
    <div style="background:#111e35;border:1px solid rgba(99,179,237,0.1);
                border-radius:8px;padding:14px 18px;margin-bottom:8px;">
      <div style="font-family:'DM Mono',monospace;font-size:11px;color:#3d5a7a;
                  letter-spacing:1px;margin-bottom:6px;">YOU ASKED</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:#63b3ed;
                  margin-bottom:10px;">{qa['q']}</div>
      <div style="font-family:'DM Mono',monospace;font-size:11px;color:#3d5a7a;
                  letter-spacing:1px;margin-bottom:6px;">ANSWER</div>
      <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:#b8cce0;
                  line-height:1.7;">{qa['a']}</div>
    </div>
    """, unsafe_allow_html=True)

col_q, col_btn = st.columns([6, 1])
with col_q:
    question = st.text_input(
        "Ask a question",
        placeholder='e.g. "What revenue guidance did management give?" or "How confident are they on margins?"',
        label_visibility="collapsed",
        key="ut_question_input",
    )
with col_btn:
    ask_btn = st.button("Ask  →", type="primary", key="ut_ask_btn")

# Example questions
st.markdown("""
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
  <span style="font-family:'DM Mono',monospace;font-size:10px;color:#2a4a6a;letter-spacing:1px;">
    TRY:
  </span>
""", unsafe_allow_html=True)

example_questions = [
    "What is the revenue guidance?",
    "How confident is management on margins?",
    "What risks did they mention?",
    "Did they raise or lower guidance?",
]
cols_ex = st.columns(len(example_questions))
for col, q_ex in zip(cols_ex, example_questions):
    with col:
        if st.button(q_ex, key=f"ex_{q_ex[:20]}", use_container_width=True):
            question = q_ex
            ask_btn  = True

if ask_btn and question and question.strip():
    with st.spinner("Analysing transcript…"):
        try:
            answer = ask_transcript(question, transcript, commitments)
            st.session_state[SS_QA_HISTORY].append({"q": question, "a": answer})
            st.rerun()
        except Exception as e:
            st.error(f"Q&A failed: {e}")
elif ask_btn:
    st.warning("Please enter a question.")

if st.session_state[SS_QA_HISTORY]:
    if st.button("🗑  Clear Q&A history"):
        st.session_state[SS_QA_HISTORY] = []
        st.rerun()