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

-- Weather snapshots (one row per round, city-wide)
CREATE TABLE IF NOT EXISTS weather_events (
    id           BIGSERIAL,
    recorded_at  TIMESTAMPTZ NOT NULL,
    temperature  FLOAT,        -- °C
    feels_like   FLOAT,        -- °C
    humidity     INT,          -- percent
    weather_main TEXT,         -- "Rain", "Clear", "Clouds", "Fog" etc.
    weather_desc TEXT,         -- "light rain", "overcast clouds" etc.
    wind_speed   FLOAT,        -- m/s
    rain_mm      FLOAT,        -- mm in last hour, 0.0 if no rain
    raw_payload  JSONB,        -- full API response
    PRIMARY KEY (id, recorded_at)
);

SELECT create_hypertable('weather_events', 'recorded_at', if_not_exists => TRUE);


-- TABLE 3: Aggregated traffic metrics per time window

CREATE TABLE IF NOT EXISTS traffic_aggregates (
    id BIGSERIAL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    location_name TEXT,
    avg_speed FLOAT,
    min_speed FLOAT,
    max_speed FLOAT,
    avg_free_flow_speed FLOAT,
    avg_congestion_ratio FLOAT,
    reading_count INT,
    closure_count INT,
    PRIMARY KEY (id, window_start)
);
SELECT create_hypertable('traffic_aggregates', 'window_start', if_not_exists => TRUE);
 
-- TABLE 4: Anomalies detected by Isolation Forest

CREATE TABLE IF NOT EXISTS anomalies (
    id BIGSERIAL,
    detected_at TIMESTAMPTZ NOT NULL,
    location_name TEXT,
    anomaly_score FLOAT,
    current_speed FLOAT,
    free_flow_speed FLOAT,
    congestion_ratio FLOAT,
    reason TEXT,
    PRIMARY KEY (id, detected_at)
);
SELECT create_hypertable('anomalies', 'detected_at', if_not_exists => TRUE);
 

-- TABLE 5: Congestion predictions from Random Forest

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL,
    predicted_at TIMESTAMPTZ NOT NULL,
    location_name TEXT,
    predicted_congestion TEXT,
    actual_congestion TEXT,
    confidence FLOAT,
    top_reason_1 TEXT,
    top_reason_2 TEXT,
    top_reason_3 TEXT,
    PRIMARY KEY (id, predicted_at)
);
SELECT create_hypertable('predictions', 'predicted_at', if_not_exists => TRUE);

-- TABLE 6: Alert log
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL,
    triggered_at TIMESTAMPTZ NOT NULL,
    location_name TEXT,
    alert_type TEXT,
    message TEXT,
    delivered BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, triggered_at)
);
SELECT create_hypertable('alerts', 'triggered_at', if_not_exists => TRUE);


-- TABLE 7: Traffic Incidents from TomTom Incidents API
CREATE TABLE IF NOT EXISTS traffic_incidents (
    id BIGSERIAL,
    fetched_at TIMESTAMPTZ NOT NULL,
    incident_id TEXT,
    incident_type TEXT,           -- Accident, Jam, Road Closed, Road Works, etc.
    icon_category INT,            -- TomTom category code (1=Accident, 6=Jam, etc.)
    magnitude TEXT,               -- Minor, Moderate, Major
    description TEXT,             -- Human-readable event description
    road_from TEXT,               -- Road/street name (start)
    road_to TEXT,                 -- Road/street name (end)
    road_numbers TEXT,            -- Highway numbers if applicable
    delay_seconds INT DEFAULT 0,  -- Extra delay caused by incident
    length_meters INT DEFAULT 0,  -- Length of affected road segment
    lat DOUBLE PRECISION,         -- Center point latitude
    lon DOUBLE PRECISION,         -- Center point longitude
    start_time TIMESTAMPTZ,       -- When the incident started
    end_time TIMESTAMPTZ,         -- When the incident is expected to end
    raw_geometry JSONB,           -- Full GeoJSON geometry
    PRIMARY KEY (id, fetched_at)
);
SELECT create_hypertable('traffic_incidents', 'fetched_at', if_not_exists => TRUE);