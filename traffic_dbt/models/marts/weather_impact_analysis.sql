SELECT
    weather_condition,
    temp_range,
    rain_level,
    visibility_impact,

    -- Speed and congestion
    ROUND(AVG(current_speed)::numeric, 1) AS avg_speed,
    ROUND(AVG(congestion_ratio)::numeric, 3) AS avg_congestion_ratio,
    ROUND(AVG(temperature)::numeric, 1) AS avg_temperature,
    ROUND(AVG(rain_mm)::numeric, 2) AS avg_rain_mm,

    -- Counts
    COUNT(*) AS total_readings,

    -- Congestion distribution
    ROUND(
        (SUM(CASE WHEN congestion_level = 'Free Flow' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_free_flow,
    ROUND(
        (SUM(CASE WHEN congestion_level IN ('Heavy', 'Severe') THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_heavy_or_worse,

    -- Compare to Clear weather baseline
    ROUND(AVG(current_speed)::numeric, 1) - (
        SELECT ROUND(AVG(s2.current_speed)::numeric, 1)
        FROM {{ ref('stg_traffic_enriched') }} s2
        WHERE s2.weather_condition = 'Clear'
    ) AS speed_diff_from_clear

FROM {{ ref('stg_traffic_enriched') }}
GROUP BY weather_condition, temp_range, rain_level, visibility_impact
ORDER BY avg_congestion_ratio ASC
