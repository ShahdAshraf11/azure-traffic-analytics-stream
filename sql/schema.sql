-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Raw events table with composite primary key (id, request_time)
CREATE TABLE raw_events (
    id BIGSERIAL,
    request_time TIMESTAMPTZ NOT NULL,
    requested_lat DOUBLE PRECISION,
    requested_lon DOUBLE PRECISION,
    location_name TEXT,
    frc TEXT,
    current_speed FLOAT,
    free_flow_speed FLOAT,
    current_travel_time INT,
    free_flow_travel_time INT,
    confidence FLOAT,
    road_closure BOOLEAN,
    raw_payload JSONB,              -- full API response
    PRIMARY KEY (id, request_time)
);

-- Convert to hypertable
SELECT create_hypertable('raw_events', 'request_time');
