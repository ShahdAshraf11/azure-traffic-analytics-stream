
-- Adds new tables for Phase C:
--   - forecasts: stores 20/30/60-min predictions
--   - ai_summaries: stores Gemini-generated insights

-- TABLE: forecasts
-- Stores 20/30/60-minute predictions from LightGBM models

CREATE TABLE IF NOT EXISTS forecasts (
    id BIGSERIAL,
    forecast_made_at TIMESTAMPTZ NOT NULL,   -- when the prediction was made
    location_name TEXT NOT NULL,
    horizon TEXT NOT NULL,                   -- "20min", "30min", or "60min"
    target_time TIMESTAMPTZ NOT NULL,        -- when the prediction is FOR
    predicted_speed FLOAT,                   -- predicted km/h
    predicted_class TEXT,                    -- "Free Flow", "Moderate", "Heavy", "Severe", "Closed"
    confidence FLOAT,                        -- max class probability (0-1)
    PRIMARY KEY (id, forecast_made_at)
);
SELECT create_hypertable('forecasts', 'forecast_made_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_forecasts_location_horizon
    ON forecasts(location_name, horizon, forecast_made_at DESC);



-- TABLE: ai_summaries
-- Stores Gemini-generated natural language city summaries
CREATE TABLE IF NOT EXISTS ai_summaries (
    id BIGSERIAL,
    generated_at TIMESTAMPTZ NOT NULL,
    summary_text TEXT NOT NULL,              -- the Gemini-generated text
    snapshot_data JSONB,                     -- the input snapshot (for debugging)
    tokens_in INT DEFAULT 0,
    tokens_out INT DEFAULT 0,
    elapsed_ms INT DEFAULT 0,
    cached BOOLEAN DEFAULT FALSE,
    error TEXT,                              -- error message if failed
    PRIMARY KEY (id, generated_at)
);
SELECT create_hypertable('ai_summaries', 'generated_at', if_not_exists => TRUE);


-- VERIFY

\echo ''
\echo 'Phase C migration complete. New tables:'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('forecasts', 'ai_summaries')
ORDER BY table_name;
