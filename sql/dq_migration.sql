
-- Adds data_quality_events table for Phase C Data Quality Pipeline.
-- TABLE: data_quality_events
-- Logs every quality check result (passed or failed)

CREATE TABLE IF NOT EXISTS data_quality_events (
    id BIGSERIAL,
    checked_at TIMESTAMPTZ NOT NULL,
    location_name TEXT,
    quality_score INT NOT NULL,         -- 0-100, higher is better
    passed BOOLEAN NOT NULL,            -- true if score >= threshold AND no fatal issues
    issues_count INT DEFAULT 0,         -- number of issues found
    issues JSONB,                       -- array of issue descriptions
    raw_message JSONB,                  -- the original message for debugging
    PRIMARY KEY (id, checked_at)
);
SELECT create_hypertable('data_quality_events', 'checked_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_dq_events_passed
    ON data_quality_events(passed, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_events_location
    ON data_quality_events(location_name, checked_at DESC);



-- VERIFY

\echo ''
\echo 'DQ migration complete. New table:'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'data_quality_events';
