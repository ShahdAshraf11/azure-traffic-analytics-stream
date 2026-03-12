-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Raw events table (archive of TomTom API responses)
CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL PRIMARY KEY,
    request_time TIMESTAMPTZ NOT NULL,          -- when we called the API
    requested_lat DOUBLE PRECISION,              -- the point we asked for
    requested_lon DOUBLE PRECISION,              -- the point we asked for
    frc TEXT,                                     -- functional road class
    current_speed FLOAT,                          -- currentSpeed
    free_flow_speed FLOAT,                        -- freeFlowSpeed
    current_travel_time INT,                       -- currentTravelTime (seconds)
    free_flow_travel_time INT,                     -- freeFlowTravelTime (seconds)
    confidence FLOAT,                              -- confidence (0‑1)
    road_closure BOOLEAN,                          -- roadClosure
    -- coordinates are stored as JSON because they are a list; we can keep them in raw_payload
    raw_payload JSONB                              -- full API response
);

-- Convert to hypertable for time-series optimization (on request_time)
SELECT create_hypertable('raw_events', 'request_time', if_not_exists => TRUE);

-- (We can add indexes later, e.g., on (request_time, frc))
