
SELECT
    location_name,
    district,
    road_class,
    hour,
    time_period,
    is_rush_hour,
    day_name,
    is_weekend,

    -- Averages
    ROUND(AVG(current_speed)::numeric, 1) AS avg_speed,
    ROUND(AVG(free_flow_speed)::numeric, 1) AS avg_free_flow,
    ROUND(AVG(congestion_ratio)::numeric, 3) AS avg_congestion_ratio,
    ROUND(AVG(temperature)::numeric, 1) AS avg_temperature,

    -- Counts
    COUNT(*) AS reading_count,
    SUM(CASE WHEN road_closure THEN 1 ELSE 0 END) AS closure_count,

    -- Congestion distribution
    SUM(CASE WHEN congestion_level = 'Free Flow' THEN 1 ELSE 0 END) AS free_flow_count,
    SUM(CASE WHEN congestion_level = 'Moderate' THEN 1 ELSE 0 END) AS moderate_count,
    SUM(CASE WHEN congestion_level = 'Heavy' THEN 1 ELSE 0 END) AS heavy_count,
    SUM(CASE WHEN congestion_level = 'Severe' THEN 1 ELSE 0 END) AS severe_count,
    SUM(CASE WHEN congestion_level = 'Closed' THEN 1 ELSE 0 END) AS closed_count,

    -- Most common congestion level this hour
    MODE() WITHIN GROUP (ORDER BY congestion_level) AS dominant_congestion

FROM {{ ref('stg_traffic_enriched') }}
GROUP BY location_name, district, road_class, hour, time_period, is_rush_hour, day_name, is_weekend
ORDER BY location_name, hour
