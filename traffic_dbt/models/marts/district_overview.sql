SELECT
    district,

    -- How many roads in this district
    COUNT(DISTINCT location_name) AS road_count,

    -- Speed and congestion
    ROUND(AVG(current_speed)::numeric, 1) AS avg_speed,
    ROUND(AVG(congestion_ratio)::numeric, 3) AS avg_congestion_ratio,

    -- Total readings
    COUNT(*) AS total_readings,

    -- Congestion percentage
    ROUND(
        (SUM(CASE WHEN congestion_level != 'Free Flow' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_congested,

    -- Dominant status
    MODE() WITHIN GROUP (ORDER BY congestion_level) AS dominant_congestion,

    -- Average weather
    ROUND(AVG(temperature)::numeric, 1) AS avg_temperature

FROM {{ ref('stg_traffic_enriched') }}
GROUP BY district
ORDER BY avg_congestion_ratio ASC
