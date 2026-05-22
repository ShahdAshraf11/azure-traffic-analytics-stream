SELECT
    -- From fact table (measures)
    f.event_time,
    f.current_speed,
    f.free_flow_speed,
    f.congestion_ratio,
    f.road_closure,
    f.confidence,
    f.temperature,
    f.rain_mm,
    f.humidity,
    f.wind_speed,

    -- From dim_location (road details)
    l.location_name,
    l.district,
    l.road_class,
    l.lat,
    l.lon,

    -- From dim_time (time details)
    t.hour,
    t.day_of_week,
    t.day_name,
    t.is_weekend,
    t.is_rush_hour,
    t.time_period,

    -- From dim_weather (weather category)
    w.condition AS weather_condition,
    w.temp_range,
    w.rain_level,
    w.visibility_impact,

    -- Computed: congestion level based on ratio
    CASE
        WHEN f.road_closure = true THEN 'Closed'
        WHEN f.congestion_ratio >= 0.75 THEN 'Free Flow'
        WHEN f.congestion_ratio >= 0.50 THEN 'Moderate'
        WHEN f.congestion_ratio >= 0.25 THEN 'Heavy'
        ELSE 'Severe'
    END AS congestion_level

FROM {{ source('warehouse', 'fact_traffic') }} f
LEFT JOIN {{ source('warehouse', 'dim_location') }} l ON f.location_key = l.location_key
LEFT JOIN {{ source('warehouse', 'dim_time') }} t ON f.time_key = t.time_key
LEFT JOIN {{ source('warehouse', 'dim_weather') }} w ON f.weather_key = w.weather_key
