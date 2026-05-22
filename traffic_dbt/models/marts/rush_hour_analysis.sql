SELECT
    location_name,
    district,
    road_class,
    is_rush_hour,

    -- Averages
    ROUND(AVG(current_speed)::numeric, 1) AS avg_speed,
    ROUND(AVG(congestion_ratio)::numeric, 3) AS avg_congestion_ratio,
    COUNT(*) AS reading_count,

    -- Congestion breakdown
    ROUND(
        (SUM(CASE WHEN congestion_level = 'Free Flow' THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_free_flow,
    ROUND(
        (SUM(CASE WHEN congestion_level IN ('Heavy', 'Severe', 'Closed') THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100,
        1
    ) AS pct_congested

FROM {{ ref('stg_traffic_enriched') }}
GROUP BY location_name, district, road_class, is_rush_hour
ORDER BY location_name, is_rush_hour
