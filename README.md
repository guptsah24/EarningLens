EarningsLens — Full Project Pipeline Overview

What it is: EarningsLens is an NLP system that reads S&P 500 earnings call transcripts, extracts what management explicitly committed to, scores how
confidently they said it, tracks whether those commitments held across quarters, and presents findings through plain-English summaries and a 
structured analyst dashboard. It serves beginner investors, brokers and experienced investors with the same underlying pipeline.

Datasets
Primary: Bose345/sp500_earnings_transcripts (HuggingFace, MIT licence) — 33,362 transcripts across 685 S&P 500 companies from 2005–2025, pre-segmented by speaker. Filtered to 5–10 companies across 2020–2024 for project scope, giving approximately 150–200 transcripts with clean multi-quarter coverage.
Evaluation: Lamini earnings-calls-qa (HuggingFace, CC-BY licence) — transcript question-answer triples used solely to evaluate RAG output quality.
Resource: Loughran-McDonald Financial Sentiment Wordlist — standard academic dictionary for financial NLP, used to score hedge language frequency per commitment.

Stage 1 — Data Loading & Filtering
Load the dataset from HuggingFace using the datasets library. Filter to selected companies and date range. Each record already contains ticker, year, quarter, and pre-structured speaker turns — no scraping required. Store filtered subset locally as JSON.
Tools: HuggingFace datasets, pandas.

Stage 2 — Preprocessing & Segmentation
Clean raw transcript text — strip boilerplate (safe harbour disclaimers, operator instructions), normalise speaker labels (CEO, CFO, Analyst, Operator), handle financial abbreviations with a custom lookup list. Split each transcript into prepared remarks and Q&A using the pre-structured speaker turns already provided by the dataset. This distinction matters because management language is measurably more hedged in Q&A than in prepared remarks.
Model: spaCy en_core_web_trf for sentence splitting and tokenisation.

Stage 3 — Forward Guidance Extraction (headline contribution)
Every sentence is passed through finbert-fls (ProsusAI, HuggingFace), which classifies each sentence as a Specific Forward-Looking Statement, Non-Specific Forward-Looking Statement, or Not Forward-Looking. Sentences classified as Specific FLS are passed to a custom slot-filling layer built with spaCy and regex that extracts three fields — the metric (gross margin, revenue, EPS), the value (44%, $4.2B), and the timeframe (Q3 2023, full year 2024). This structured record is written to a SQLite database. The slot-filling layer is the original technical contribution of the project.
Models: finbert-fls for classification, spaCy and regex for slot filling.

Stage 4 — Hedge & Credibility Scoring
Each extracted forward-looking statement is scored for confidence. The Loughran-McDonald wordlist gives a hedge word frequency score based on uncertainty language — may, could, approximately, subject to change. finbert-tone (ProsusAI, HuggingFace) gives a positive/neutral/negative tone score per sentence. These two signals are combined into a single hedge score between 0 and 1, stored alongside the structured record. A score close to 1 means confident and specific. A score close to 0 means vague and heavily qualified.
Models: finbert-tone, Loughran-McDonald wordlist.

Stage 5 — Cross-Quarter Credibility Tracking (headline contribution)
The SQLite database now holds structured guidance records across multiple quarters per company. When a new transcript is processed, the system queries prior quarters for the same ticker and compares records on the same metric — flagging raises, misses, and withdrawals automatically. For rephrased commitments, sentence-transformers (all-MiniLM-L6-v2, HuggingFace) computes cosine similarity between current and prior guidance sentences. Above a similarity threshold of 0.75 the system treats them as the same commitment and compares values. The hedge score trend per metric is also tracked over time. Output is a guidance delta table per company showing metric, prior guidance, current guidance, change direction, and hedge score trend across quarters.
Models: sentence-transformers all-MiniLM-L6-v2. Tools: SQLite, pandas.

Stage 6 — Sentiment Analysis (supporting)
FinBERT base (ProsusAI, HuggingFace) runs across each transcript producing call-level and section-level sentiment scores separately for prepared remarks and Q&A. VADER (NLTK) runs in parallel as a fast baseline for comparison. The Loughran-McDonald wordlist serves as a second baseline. These scores provide broader context — a company with deteriorating sentiment and increasingly hedged guidance is a stronger signal than either alone.
Models: FinBERT base, VADER, Loughran-McDonald wordlist.

Stage 7 — LLM Summarisation & RAG (supporting)
LLM summarisation: structured guidance records, hedge scores, and delta flags are passed as context to a Claude or GPT-4 API call, prompted to produce a 3–5 bullet plain-English summary. The LLM summarises structured pipeline outputs — not the raw transcript — making summaries more precise and grounded than a generic chatbot response.
RAG pipeline: transcripts are chunked into sentence-level segments, embedded with sentence-transformers, and stored in a FAISS vector index via LangChain. Users ask natural language questions and receive grounded, cited answers retrieved directly from the transcript. Evaluated against Lamini earnings-calls-qa.
Models: Claude, GPT-4 API or other open source models (Gemma 4 which was just recently launched as an open source tool), sentence-transformers, FAISS. Tools: LangChain.

Stage 8 — Agentic Interpretation Layer
An agentic layer automatically reasons over the guidance delta table and hedge score trends for a company and surfaces the most significant credibility shifts without user prompting — for example flagging that gross margin guidance has been revised downward three consecutive quarters while the hedge score declined from 0.81 to 0.49. Implemented as a structured prompt to the same LLM API used in Stage 7, triggered automatically when a company dashboard is loaded.
Model: Claude or GPT-4 API.

Stage 9 — Dashboard
Streamlit single-page app. Users select a company and quarter and see five things: a plain-English LLM summary grounded in pipeline outputs, a guidance delta table with colour-coded raise/miss/withdrawal flags, a hedge score trend chart per metric built with Plotly, an automatically surfaced credibility alert from the agentic layer, and a natural language Q&A box powered by the RAG pipeline. CSV export available. Deployed to HuggingFace Spaces.
Tools: Streamlit, Plotly, HuggingFace Spaces.
