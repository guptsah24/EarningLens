CREATE TABLE IF NOT EXISTS companies (
    company_id   SERIAL PRIMARY KEY,
    ticker       TEXT UNIQUE NOT NULL,
    company_name TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id  TEXT PRIMARY KEY,
    company_id     INTEGER REFERENCES companies(company_id),
    quarter        INTEGER,
    year           INTEGER
);

CREATE TABLE IF NOT EXISTS commitments (
    commitment_id         SERIAL PRIMARY KEY,
    transcript_id         TEXT    REFERENCES transcripts(transcript_id),
    company_id            INTEGER REFERENCES companies(company_id),
    quarter               INTEGER,
    year                  INTEGER,
    sentence_text         TEXT,
    sentence_hash         TEXT,
    metric                TEXT,
    value                 TEXT,
    timeframe             TEXT,
    hedge_score           REAL,
    fls_label             TEXT,
    status                TEXT DEFAULT 'Pending',
    matched_commitment_id INTEGER
);

CREATE TABLE IF NOT EXISTS sentiment_scores (
    score_id       SERIAL PRIMARY KEY,
    transcript_id  TEXT REFERENCES transcripts(transcript_id),
    segment_type   TEXT,
    finbert_score  REAL,
    vader_score    REAL
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id    SERIAL PRIMARY KEY,
    ticker        TEXT,
    company_name  TEXT,
    quarter       INTEGER,
    year          INTEGER,
    summary_text  TEXT,
    n_commitments INTEGER
);

CREATE TABLE credibility_summary (
    id                 BIGSERIAL PRIMARY KEY,
    ticker             TEXT NOT NULL,
    company_name       TEXT,
    delivered          INTEGER DEFAULT 0,
    raised             INTEGER DEFAULT 0,
    missed             INTEGER DEFAULT 0,
    total_resolved     INTEGER DEFAULT 0,
    credibility        FLOAT,
    mean_hedge         FLOAT,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commitments_company  ON commitments(company_id);
CREATE INDEX IF NOT EXISTS idx_commitments_quarter  ON commitments(year, quarter);
CREATE INDEX IF NOT EXISTS idx_commitments_status   ON commitments(status);
CREATE INDEX IF NOT EXISTS idx_sentiment_transcript ON sentiment_scores(transcript_id);
CREATE INDEX IF NOT EXISTS idx_summaries_ticker  ON summaries(ticker);
CREATE INDEX IF NOT EXISTS idx_summaries_quarter ON summaries(year, quarter);
CREATE INDEX IF NOT EXISTS idx_credibility_ticker ON credibility_summary(ticker);