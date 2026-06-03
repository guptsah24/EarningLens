"""
rag.py
Retrieval-Augmented Generation Q&A over commitment sentences.
Uses a FAISS index + faiss_meta.parquet for retrieval,
then calls Ollama gemma3:12b to generate the answer.
Falls back to a retrieval-only answer when Ollama is unavailable.
"""

from __future__ import annotations
import os
import json
import textwrap
import requests
import numpy as np
import pandas as pd
import streamlit as st

OLLAMA_URL    = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL  = os.environ.get("OLLAMA_MODEL", "gemma3:12b")
FAISS_INDEX   = os.environ.get("FAISS_INDEX_PATH", "faiss.index")
FAISS_META    = os.environ.get("FAISS_META_PATH", "faiss_meta.parquet")
TOP_K         = 5


@st.cache_resource(show_spinner=False)
def _load_faiss():
    """Load FAISS index and metadata once per session."""
    try:
        import faiss  # type: ignore
        index = faiss.read_index(FAISS_INDEX)
        meta  = pd.read_parquet(FAISS_META)
        return index, meta
    except Exception as e:
        return None, None


@st.cache_resource(show_spinner=False)
def _load_embedder():
    """Load a lightweight sentence embedding model."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _retrieve(query: str, ticker_filter: str | None) -> pd.DataFrame:
    """Embed the query and retrieve top-K matching commitments."""
    index, meta = _load_faiss()
    embedder    = _load_embedder()

    if index is None or embedder is None:
        return pd.DataFrame()

    q_vec = embedder.encode([query]).astype("float32")
    D, I  = index.search(q_vec, TOP_K * 3)  # over-retrieve then filter

    results = meta.iloc[I[0]].copy()
    results["distance"] = D[0]

    if ticker_filter:
        filtered = results[results["ticker"].str.upper() == ticker_filter.upper()]
        if not filtered.empty:
            results = filtered

    return results.head(TOP_K).reset_index(drop=True)


def _build_context(retrieved: pd.DataFrame) -> str:
    """Format retrieved rows as a context string for the LLM."""
    lines = []
    for _, row in retrieved.iterrows():
        lines.append(
            f"[{row.get('ticker','?')} Q{row.get('quarter','?')} {row.get('year','?')}] "
            f"{row.get('metric','?')}: {row.get('sentence', row.get('q_guidance', ''))}"
        )
    return "\n".join(lines)


def _call_ollama_qa(question: str, context: str) -> str | None:
    prompt = textwrap.dedent(f"""
        You are a financial analyst assistant. Answer the question using ONLY the 
        provided source commitments. If the answer is not in the sources, say so.
        Be concise (3–5 sentences max).

        Sources:
        {context}

        Question: {question}

        Answer:
    """).strip()

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        return None


def rag_status() -> dict:
    """
    Returns a dict describing whether FAISS + embedder are ready.
    Call this from the sidebar or dashboard to surface RAG health to users.
    {
        "faiss_ok":    bool,
        "embedder_ok": bool,
        "n_vectors":   int | None,
        "message":     str,
    }
    """
    index, meta = _load_faiss()
    embedder    = _load_embedder()

    faiss_ok    = index is not None and meta is not None
    embedder_ok = embedder is not None
    n_vectors   = int(index.ntotal) if faiss_ok else None

    if faiss_ok and embedder_ok:
        msg = f"RAG ready · {n_vectors:,} indexed commitments"
    elif not faiss_ok and not embedder_ok:
        msg = "RAG unavailable — faiss.index, faiss_meta.parquet, and sentence-transformers not found"
    elif not faiss_ok:
        msg = "RAG unavailable — faiss.index / faiss_meta.parquet missing"
    else:
        msg = "RAG unavailable — sentence-transformers not installed"

    return {
        "faiss_ok":    faiss_ok,
        "embedder_ok": embedder_ok,
        "n_vectors":   n_vectors,
        "message":     msg,
    }


def answer_question(question: str, ticker_filter: str | None = None) -> dict:
    """
    Main entry point for Q&A.
    Returns:
        {
            "answer":   str,
            "sources":  list[dict]  — each has ticker, quarter, year, metric, sentence
        }
    """
    if not question.strip():
        return {"answer": "", "sources": []}

    retrieved = _retrieve(question, ticker_filter)

    if retrieved.empty:
        return {
            "answer": "No relevant commitments found in the index. "
                      "Ensure faiss.index and faiss_meta.parquet are present.",
            "sources": [],
        }

    context = _build_context(retrieved)
    answer  = _call_ollama_qa(question, context)

    if not answer:
        # Fallback: return retrieved sentences as the answer
        answer = "Here are the most relevant commitments I found:\n\n" + context

    sources = retrieved[
        [c for c in ["ticker", "quarter", "year", "metric", "sentence", "q_guidance"]
         if c in retrieved.columns]
    ].to_dict(orient="records")

    return {"answer": answer, "sources": sources}