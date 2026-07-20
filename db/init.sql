-- Every document we've ever seen. The unique constraint on url is what
-- makes this idempotent — rerunning the check never re-alerts on a
-- document we've already reported.
CREATE TABLE IF NOT EXISTS cbn_documents (
    id           SERIAL PRIMARY KEY,
    url          TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    sources      JSONB,               -- e.g. ["Circulars", "Press Releases"]
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notified_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cbn_documents_first_seen ON cbn_documents(first_seen_at);

-- Failed scrape attempts land here instead of vanishing — same
-- dead-letter pattern as the job search and invoice automation projects.
CREATE TABLE IF NOT EXISTS cbn_dead_letter (
    id            SERIAL PRIMARY KEY,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
