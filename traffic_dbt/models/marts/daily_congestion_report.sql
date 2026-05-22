SELECT
    DATE(event_time) AS report_date,
    location_name,
    district,
    road_class,

    -- Speed statistics
    ROUND(AVG(current_speed)::numeric, 1) AS avg_speed,
    ROUND(MIN(current_speed)::numeric, 1) AS min_speed,
    ROUND(MAX(current_speed)::numeric, 1) AS max_speed,
    ROUND(AVG(free_flow_speed)::numeric, 1) AS avg_free_flow,
    ROUND(AVG(congestion_ratio)::numeric, 3) AS avg_congestion_ratio,

    -- Readings
    COUNT(*) AS total_readings,
    SUM(CASE WHEN road_closure THEN 1 ELSE 0 END) AS closure_count,

    -- Congestion percentage (how often was this road NOT free flow?)
    ROUND(
        (SUM(CASE WHEN congestion_level != 'Free Flow' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_congested,

    -- Dominant congestion level for the day
    MODE() WITHIN GROUP (ORDER BY congestion_level) AS dominant_congestion,

    -- Weather for the day
    ROUND(AVG(temperature)::numeric, 1) AS avg_temperature,
    ROUND(SUM(COALESCE(rain_mm, 0))::numeric, 2) AS total_rain_mm,
    MODE() WITHIN GROUP (ORDER BY weather_condition) AS dominant_weather

FROM {{ ref('stg_traffic_enriched') }}
GROUP BY DATE(event_time), location_name, district, road_class
ORDER BY report_date DESC, avg_congestion_ratio ASC
