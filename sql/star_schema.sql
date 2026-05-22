
-- Create a separate schema so warehouse tables don't mix with operational tables
CREATE SCHEMA IF NOT EXISTS warehouse;



-- DIMENSION 1: Location
-- One row per monitored road. Changes rarely (only when you add roads).

CREATE TABLE IF NOT EXISTS warehouse.dim_location (
    location_key SERIAL PRIMARY KEY,
    location_name TEXT UNIQUE NOT NULL,     -- "Tahrir Square"
    lat DOUBLE PRECISION,                   -- 30.0444
    lon DOUBLE PRECISION,                   -- 31.2357
    district TEXT,                          -- "Downtown", "Giza", "Maadi", etc.
    road_class TEXT                         -- "Highway", "Main Road", "Bridge", etc.
);

-- Pre-populate with your 25 roads
INSERT INTO warehouse.dim_location (location_name, lat, lon, district, road_class) VALUES
    ('Tahrir Square', 30.0444, 31.2357, 'Downtown', 'Square'),
    ('Nasr City Ring Road', 30.0626, 31.3417, 'Nasr City', 'Highway'),
    ('October Bridge', 30.0603, 31.2446, 'Downtown', 'Bridge'),
    ('El-Rawda St', 30.015822, 31.223920, 'Old Cairo', 'Main Road'),
    ('Maadi Corniche', 29.957459, 31.250348, 'Maadi', 'Corniche'),
    ('El-Gomhoreya St', 30.0499, 31.2466, 'Downtown', 'Main Road'),
    ('El-Gaish St', 30.052268, 31.254252, 'Downtown', 'Main Road'),
    ('Salah Salem Road', 30.0396, 31.2657, 'Heliopolis', 'Highway'),
    ('Ramses St', 30.052613, 31.237925, 'Downtown', 'Main Road'),
    ('Talaat Harb St', 30.0506, 31.2404, 'Downtown', 'Main Road'),
    ('El Haram St', 30.015433, 31.214553, 'Giza', 'Main Road'),
    ('Nile Corniche', 30.047107, 31.231616, 'Downtown', 'Corniche'),
    ('26th of July Corridor', 30.063321, 31.167581, 'Mohandessin', 'Highway'),
    ('Gamal Abd El-Nasser Rd', 30.051973, 31.216775, 'Dokki', 'Main Road'),
    ('Shobra St', 30.092088, 31.245208, 'Shobra', 'Main Road'),
    ('Abdulaziz Al Saud St', 30.023352, 31.223223, 'Old Cairo', 'Main Road'),
    ('Al Manial St', 30.012794, 31.224867, 'Manial', 'Main Road'),
    ('Al Malik Al Mozafar St', 30.014387, 31.223665, 'Old Cairo', 'Main Road'),
    ('Amro Ibn Al Aas St', 30.013521, 31.229385, 'Old Cairo', 'Main Road'),
    ('Magra El-Eyoun St', 30.020851, 31.240715, 'Old Cairo', 'Main Road'),
    ('Autostorad St', 29.997227, 31.278652, 'Maadi', 'Highway'),
    ('El-Qobba Bridge', 30.100566, 31.305483, 'El-Qobba', 'Bridge'),
    ('King Faisal St', 30.004008, 31.174183, 'Giza', 'Main Road'),
    ('Ring Road', 29.999456, 31.119034, 'Giza', 'Highway'),
    ('Ahmed Oraby St', 30.062267, 31.212831, 'Dokki', 'Main Road')
ON CONFLICT (location_name) DO NOTHING;



-- DIMENSION 2: Time
-- One row per hour of the day × day type combination.
-- Pre-populated with all possible time slots.

CREATE TABLE IF NOT EXISTS warehouse.dim_time (
    time_key SERIAL PRIMARY KEY,
    hour INT NOT NULL,                      -- 0-23
    day_of_week INT NOT NULL,               -- 0=Monday, 6=Sunday
    day_name TEXT NOT NULL,                  -- "Monday", "Tuesday", etc.
    is_weekend BOOLEAN NOT NULL,            -- true for Friday/Saturday (Egypt weekend)
    is_rush_hour BOOLEAN NOT NULL,          -- true for 7-9 AM and 4-7 PM
    time_period TEXT NOT NULL,              -- "Early Morning", "Morning Rush", "Midday", etc.
    UNIQUE (hour, day_of_week)
);

-- Pre-populate all 168 combinations (24 hours × 7 days)
INSERT INTO warehouse.dim_time (hour, day_of_week, day_name, is_weekend, is_rush_hour, time_period)
SELECT
    h,
    d,
    CASE d WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
           WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
           WHEN 6 THEN 'Saturday' END,
    d IN (5, 6),  -- Egypt weekend: Friday(5) + Saturday(6)
    h BETWEEN 7 AND 9 OR h BETWEEN 16 AND 19,
    CASE
        WHEN h BETWEEN 0 AND 5 THEN 'Late Night'
        WHEN h BETWEEN 6 AND 6 THEN 'Early Morning'
        WHEN h BETWEEN 7 AND 9 THEN 'Morning Rush'
        WHEN h BETWEEN 10 AND 15 THEN 'Midday'
        WHEN h BETWEEN 16 AND 19 THEN 'Evening Rush'
        WHEN h BETWEEN 20 AND 23 THEN 'Night'
    END
FROM generate_series(0, 23) AS h, generate_series(0, 6) AS d
ON CONFLICT (hour, day_of_week) DO NOTHING;



-- DIMENSION 3: Weather
-- One row per weather condition category.

CREATE TABLE IF NOT EXISTS warehouse.dim_weather (
    weather_key SERIAL PRIMARY KEY,
    condition TEXT UNIQUE NOT NULL,         -- "Clear", "Clouds", "Rain", "Sand", etc.
    temp_range TEXT,                        -- "Cold (<15°C)", "Mild (15-25°C)", "Hot (25-35°C)", "Very Hot (>35°C)"
    rain_level TEXT,                        -- "None", "Light", "Moderate", "Heavy"
    visibility_impact TEXT                  -- "Good", "Reduced", "Poor"
);

INSERT INTO warehouse.dim_weather (condition, temp_range, rain_level, visibility_impact) VALUES
    ('Clear', 'Hot (25-35°C)', 'None', 'Good'),
    ('Clouds', 'Mild (15-25°C)', 'None', 'Good'),
    ('Rain', 'Mild (15-25°C)', 'Moderate', 'Reduced'),
    ('Drizzle', 'Mild (15-25°C)', 'Light', 'Good'),
    ('Thunderstorm', 'Mild (15-25°C)', 'Heavy', 'Poor'),
    ('Sand', 'Hot (25-35°C)', 'None', 'Poor'),
    ('Dust', 'Hot (25-35°C)', 'None', 'Poor'),
    ('Fog', 'Mild (15-25°C)', 'None', 'Poor'),
    ('Mist', 'Mild (15-25°C)', 'None', 'Reduced'),
    ('Haze', 'Hot (25-35°C)', 'None', 'Reduced'),
    ('Smoke', 'Hot (25-35°C)', 'None', 'Poor'),
    ('Snow', 'Cold (<15°C)', 'None', 'Poor')
ON CONFLICT (condition) DO NOTHING;



-- FACT TABLE: Traffic Readings
-- The main analytical table. Each row = one traffic reading
-- with foreign keys pointing to the dimension tables.
-- This is what Power BI queries.
CREATE TABLE IF NOT EXISTS warehouse.fact_traffic (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,        -- When this reading was taken
    location_key INT REFERENCES warehouse.dim_location(location_key),
    time_key INT REFERENCES warehouse.dim_time(time_key),
    weather_key INT REFERENCES warehouse.dim_weather(weather_key),
    
    -- Measures (the numbers Power BI aggregates)
    current_speed FLOAT,                    -- km/h
    free_flow_speed FLOAT,                  -- km/h
    congestion_ratio FLOAT,                 -- current/freeflow (0-1)
    road_closure BOOLEAN,
    confidence FLOAT,
    
    -- Weather measures
    temperature FLOAT,
    rain_mm FLOAT,
    humidity INT,
    wind_speed FLOAT
);

-- Index for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_fact_traffic_time ON warehouse.fact_traffic(event_time);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_location ON warehouse.fact_traffic(location_key);