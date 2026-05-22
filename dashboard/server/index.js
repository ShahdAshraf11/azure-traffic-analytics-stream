/**
 * Traffic Analytics Dashboard — API Server
 * 
 * Connects to PostgreSQL and serves JSON endpoints for the React frontend.
 * 
 * Endpoints:
 *   GET /api/predictions/latest     → Latest prediction per location (for map)
 *   GET /api/anomalies              → Recent anomalies (for feed)
 *   GET /api/aggregates             → Window aggregates (for charts)
 *   GET /api/weather/latest         → Current weather
 *   GET /api/health                 → System health metrics
 *   GET /api/locations              → All monitored locations with coordinates
 *   GET /api/speed-history/:location → Speed history for one location
 *   GET /api/congestion-distribution → Congestion level counts by hour
 * 
 * Run: cd dashboard/server && npm install && npm start
 */

require("dotenv").config();
const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");

const app = express();
const PORT = process.env.PORT || 5000;

// Allow React dev server (port 3000) to call this API
app.use(cors());
app.use(express.json());

// ── Database connection pool ──
// A pool keeps multiple connections open and reuses them (faster than opening a new one per request)
const pool = new Pool({
  host: process.env.PGHOST,
  port: process.env.PGPORT,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
});

// Test connection on startup
pool.query("SELECT NOW()")
  .then(() => console.log("✅ Connected to PostgreSQL"))
  .catch((err) => console.error("❌ PostgreSQL connection failed:", err.message));


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 1: Latest prediction per location (for the map)
// ═══════════════════════════════════════════════════════════
app.get("/api/predictions/latest", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT DISTINCT ON (p.location_name)
        p.location_name,
        p.predicted_congestion,
        p.actual_congestion,
        p.confidence,
        p.top_reason_1,
        p.top_reason_2,
        p.top_reason_3,
        p.predicted_at,
        r.requested_lat as lat,
        r.requested_lon as lon,
        r.current_speed,
        r.free_flow_speed,
        r.road_closure
      FROM predictions p
      JOIN (
        SELECT DISTINCT ON (location_name)
          location_name, requested_lat, requested_lon,
          current_speed, free_flow_speed, road_closure
        FROM raw_events
        ORDER BY location_name, request_time DESC
      ) r ON p.location_name = r.location_name
      ORDER BY p.location_name, p.predicted_at DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching predictions:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 2: Recent anomalies (for the anomaly feed)
// ═══════════════════════════════════════════════════════════
app.get("/api/anomalies", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  try {
    const result = await pool.query(`
      SELECT detected_at, location_name, anomaly_score,
             current_speed, free_flow_speed, congestion_ratio, reason
      FROM anomalies
      WHERE detected_at > NOW() - INTERVAL '${hours} hours'
      ORDER BY detected_at DESC
      LIMIT 100
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching anomalies:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 2b: Recent alerts (for alert bar + alert page)
// ═══════════════════════════════════════════════════════════
app.get("/api/alerts", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  try {
    const result = await pool.query(`
      SELECT triggered_at, location_name, alert_type, message, delivered
      FROM alerts
      WHERE triggered_at > NOW() - INTERVAL '${hours} hours'
      ORDER BY triggered_at DESC
      LIMIT 100
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching alerts:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 2c: Traffic incidents (filtered to monitored roads)
//  Only returns incidents within ~500m of the 25 monitored locations
// ═══════════════════════════════════════════════════════════
app.get("/api/incidents", async (req, res) => {
  const hours = parseInt(req.query.hours) || 2;
  try {
    const result = await pool.query(`
      WITH monitored_locations AS (
        SELECT DISTINCT ON (location_name)
          location_name,
          requested_lat AS lat,
          requested_lon AS lon
        FROM raw_events
        WHERE request_time > NOW() - INTERVAL '24 hours'
          AND requested_lat IS NOT NULL AND requested_lon IS NOT NULL
        ORDER BY location_name, request_time DESC
      ),
      recent_incidents AS (
        SELECT DISTINCT ON (incident_id)
          i.fetched_at, i.incident_id, i.incident_type, i.icon_category,
          i.magnitude, i.description, i.road_from, i.road_to,
          i.delay_seconds, i.length_meters, i.lat, i.lon,
          i.start_time, i.end_time
        FROM traffic_incidents i
        WHERE i.fetched_at > NOW() - INTERVAL '${hours} hours'
          AND i.lat IS NOT NULL AND i.lon IS NOT NULL
        ORDER BY i.incident_id, i.fetched_at DESC
      ),
      matched AS (
        SELECT DISTINCT ON (ml.location_name)
          ri.*,
          ml.location_name AS near_road,
          ABS(ri.lat - ml.lat) + ABS(ri.lon - ml.lon) AS distance
        FROM recent_incidents ri
        JOIN monitored_locations ml
          ON ABS(ri.lat - ml.lat) < 0.002
          AND ABS(ri.lon - ml.lon) < 0.002
        ORDER BY ml.location_name, distance ASC
      )
      SELECT * FROM matched
      ORDER BY fetched_at DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching incidents:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 3: Window aggregates (for speed trend charts)
// ═══════════════════════════════════════════════════════════
app.get("/api/aggregates", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  try {
    const result = await pool.query(`
      SELECT window_start, window_end, location_name,
             avg_speed, min_speed, max_speed,
             avg_free_flow_speed, avg_congestion_ratio,
             reading_count, closure_count
      FROM traffic_aggregates
      WHERE window_start > NOW() - INTERVAL '${hours} hours'
      ORDER BY window_start DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching aggregates:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 4: Latest weather
// ═══════════════════════════════════════════════════════════
app.get("/api/weather/latest", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT recorded_at, temperature, feels_like, humidity,
             weather_main, weather_desc, wind_speed, rain_mm
      FROM weather_events
      ORDER BY recorded_at DESC
      LIMIT 1
    `);
    res.json(result.rows[0] || {});
  } catch (err) {
    console.error("Error fetching weather:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════
//  ENDPOINT 5: System health metrics
// ═══════════════════════════════════════════════════════════
app.get("/api/health", async (req, res) => {
  try {
    const [rawCount, predCount, anomCount, aggCount, freshness] = await Promise.all([
      pool.query("SELECT COUNT(*) as count FROM raw_events WHERE request_time > NOW() - INTERVAL '24 hours'"),
      pool.query("SELECT COUNT(*) as count FROM predictions WHERE predicted_at > NOW() - INTERVAL '24 hours'"),
      pool.query("SELECT COUNT(*) as count FROM anomalies WHERE detected_at > NOW() - INTERVAL '24 hours'"),
      pool.query("SELECT COUNT(*) as count FROM traffic_aggregates WHERE window_start > NOW() - INTERVAL '24 hours'"),
      pool.query(`
        SELECT location_name,
               MAX(request_time) as last_reading,
               EXTRACT(EPOCH FROM (NOW() - MAX(request_time))) as age_seconds
        FROM raw_events
        GROUP BY location_name
        ORDER BY last_reading DESC
      `),
    ]);

    // ── Overall prediction accuracy (last 24h) ──
    const accuracy = await pool.query(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN predicted_congestion = actual_congestion THEN 1 ELSE 0 END) as correct
      FROM predictions
      WHERE predicted_at > NOW() - INTERVAL '24 hours'
        AND actual_congestion IS NOT NULL
    `);
    const acc = accuracy.rows[0];
    const accuracyPct = acc.total > 0 ? ((acc.correct / acc.total) * 100).toFixed(1) : 0;

    // ── REAL per-class accuracy (last 7 days) ──
    const perClass = await pool.query(`
      SELECT
        actual_congestion as level,
        COUNT(*) as total,
        SUM(CASE WHEN predicted_congestion = actual_congestion THEN 1 ELSE 0 END) as correct
      FROM predictions
      WHERE predicted_at > NOW() - INTERVAL '7 days'
        AND actual_congestion IS NOT NULL
      GROUP BY actual_congestion
    `);
    const perClassAccuracy = {};
    perClass.rows.forEach(row => {
      const t = parseInt(row.total);
      perClassAccuracy[row.level] = t > 0
        ? Math.round((parseInt(row.correct) / t) * 100)
        : 0;
    });

    // ── REAL API/data success rate (DQ pass rate, last 24h) ──
    const dqRate = await pool.query(`
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed
      FROM data_quality_events
      WHERE checked_at > NOW() - INTERVAL '24 hours'
    `);
    const dq = dqRate.rows[0];
    const apiSuccessRate = dq.total > 0
      ? ((dq.passed / dq.total) * 100).toFixed(1)
      : 100;

    // ── Day-over-day deltas (records, accuracy, DQ rate) ──
    const deltas = await pool.query(`
      SELECT
        (SELECT COUNT(*) FROM raw_events
          WHERE request_time > NOW() - INTERVAL '24 hours') as records_today,
        (SELECT COUNT(*) FROM raw_events
          WHERE request_time > NOW() - INTERVAL '48 hours'
            AND request_time <= NOW() - INTERVAL '24 hours') as records_yesterday,

        (SELECT COALESCE(AVG(CASE WHEN predicted_congestion = actual_congestion THEN 100.0 ELSE 0 END), 0)
          FROM predictions
          WHERE predicted_at > NOW() - INTERVAL '24 hours'
            AND actual_congestion IS NOT NULL) as acc_today,
        (SELECT COALESCE(AVG(CASE WHEN predicted_congestion = actual_congestion THEN 100.0 ELSE 0 END), 0)
          FROM predictions
          WHERE predicted_at > NOW() - INTERVAL '48 hours'
            AND predicted_at <= NOW() - INTERVAL '24 hours'
            AND actual_congestion IS NOT NULL) as acc_yesterday,

        (SELECT COALESCE(AVG(CASE WHEN passed THEN 100.0 ELSE 0 END), 0)
          FROM data_quality_events
          WHERE checked_at > NOW() - INTERVAL '24 hours') as dq_today,
        (SELECT COALESCE(AVG(CASE WHEN passed THEN 100.0 ELSE 0 END), 0)
          FROM data_quality_events
          WHERE checked_at > NOW() - INTERVAL '48 hours'
            AND checked_at <= NOW() - INTERVAL '24 hours') as dq_yesterday
    `);
    const dd = deltas.rows[0];

    const recToday = parseFloat(dd.records_today);
    const recYesterday = parseFloat(dd.records_yesterday);
    const recordsChange = recYesterday > 0
      ? (((recToday - recYesterday) / recYesterday) * 100).toFixed(1) : 0;
    const accuracyChange = (parseFloat(dd.acc_today) - parseFloat(dd.acc_yesterday)).toFixed(1);
    const apiChange = (parseFloat(dd.dq_today) - parseFloat(dd.dq_yesterday)).toFixed(1);

    res.json({
      raw_events_24h: parseInt(rawCount.rows[0].count),
      predictions_24h: parseInt(predCount.rows[0].count),
      anomalies_24h: parseInt(anomCount.rows[0].count),
      aggregations_24h: parseInt(aggCount.rows[0].count),
      accuracy_24h: parseFloat(accuracyPct),
      per_class_accuracy: perClassAccuracy,
      api_success_rate: parseFloat(apiSuccessRate),
      records_change_pct: parseFloat(recordsChange),
      accuracy_change_pct: parseFloat(accuracyChange),
      api_change_pct: parseFloat(apiChange),
      location_freshness: freshness.rows,
    });
  } catch (err) {
    console.error("Error fetching health:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 6: All monitored locations with latest data
// ═══════════════════════════════════════════════════════════
app.get("/api/locations", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT DISTINCT ON (location_name)
        location_name, requested_lat, requested_lon, frc,
        current_speed, free_flow_speed, confidence,
        road_closure, request_time
      FROM raw_events
      ORDER BY location_name, request_time DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching locations:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 7: Speed history for one location (for charts)
// ═══════════════════════════════════════════════════════════
app.get("/api/speed-history/:location", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  const location = req.params.location;
  try {
    const result = await pool.query(`
      SELECT request_time, current_speed, free_flow_speed,
             confidence, road_closure
      FROM raw_events
      WHERE location_name = $1
        AND request_time > NOW() - INTERVAL '${hours} hours'
      ORDER BY request_time ASC
    `, [location]);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching speed history:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 8: Congestion level distribution by hour
// ═══════════════════════════════════════════════════════════
app.get("/api/congestion-distribution", async (req, res) => {
  const days = parseInt(req.query.days) || 7;
  try {
    const result = await pool.query(`
      SELECT
        EXTRACT(HOUR FROM predicted_at)::int as hour,
        predicted_congestion as level,
        COUNT(*) as count
      FROM predictions
      WHERE predicted_at > NOW() - INTERVAL '${days} days'
      GROUP BY hour, level
      ORDER BY hour, level
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching distribution:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// PHASE C ADDITIONS to dashboard/server/index.js
// ═══════════════════════════════════════════════════════════════════════════
//
// HOW TO APPLY:
// Open dashboard/server/index.js
// Find the line that says: //  START SERVER
// Just BEFORE that section, paste ALL the code below.
//
// Then restart the server: npm start
//
// ═══════════════════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 9: Latest forecasts per location (Phase B/C)
//  Returns the most recent forecast for each (location, horizon) pair.
//  Used by the Forecast Panel to show "next 20/30/60 min" predictions.
// ═══════════════════════════════════════════════════════════
app.get("/api/forecasts/latest", async (req, res) => {
  try {
    const result = await pool.query(`
      WITH latest_forecasts AS (
        SELECT DISTINCT ON (location_name, horizon)
          forecast_made_at,
          location_name,
          horizon,
          target_time,
          predicted_speed,
          predicted_class,
          confidence
        FROM forecasts
        WHERE forecast_made_at > NOW() - INTERVAL '15 minutes'
        ORDER BY location_name, horizon, forecast_made_at DESC
      ),
      current_speeds AS (
        SELECT DISTINCT ON (location_name)
          location_name,
          current_speed,
          free_flow_speed,
          requested_lat AS lat,
          requested_lon AS lon
        FROM raw_events
        WHERE request_time > NOW() - INTERVAL '10 minutes'
        ORDER BY location_name, request_time DESC
      )
      SELECT
        c.location_name,
        c.current_speed,
        c.free_flow_speed,
        c.lat,
        c.lon,
        json_object_agg(
          f.horizon,
          json_build_object(
            'predicted_speed', f.predicted_speed,
            'predicted_class', f.predicted_class,
            'confidence', f.confidence,
            'target_time', f.target_time,
            'forecast_made_at', f.forecast_made_at
          )
        ) FILTER (WHERE f.horizon IS NOT NULL) AS forecasts
      FROM current_speeds c
      LEFT JOIN latest_forecasts f ON c.location_name = f.location_name
      GROUP BY c.location_name, c.current_speed, c.free_flow_speed, c.lat, c.lon
      ORDER BY c.location_name
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching forecasts:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 10: Latest AI summary
//  Returns the most recent Gemini-generated summary text.
//  Used by the AI Summary Banner at the top of the dashboard.
// ═══════════════════════════════════════════════════════════
app.get("/api/ai-summary/latest", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT
        generated_at,
        summary_text,
        snapshot_data,
        tokens_in,
        tokens_out,
        elapsed_ms,
        cached,
        error
      FROM ai_summaries
      WHERE error IS NULL OR error = ''
      ORDER BY generated_at DESC
      LIMIT 1
    `);
    res.json(result.rows[0] || null);
  } catch (err) {
    console.error("Error fetching AI summary:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 11: Data quality statistics
//  Returns aggregate DQ metrics for the last N hours.
//  Used by the Data Quality Widget and Data Quality page.
// ═══════════════════════════════════════════════════════════
app.get("/api/data-quality/stats", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  try {
    // Overall stats
    const overall = await pool.query(`
      SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS passed_count,
        SUM(CASE WHEN NOT passed THEN 1 ELSE 0 END) AS failed_count,
        SUM(CASE WHEN issues_count > 0 AND passed THEN 1 ELSE 0 END) AS warning_count,
        AVG(quality_score)::int AS avg_score,
        MIN(quality_score) AS min_score,
        MAX(quality_score) AS max_score
      FROM data_quality_events
      WHERE checked_at > NOW() - INTERVAL '${hours} hours'
    `);

    // Top issues — unnest the JSONB array of issues to count by check type
    const topIssues = await pool.query(`
      SELECT
        issue->>'check' AS check_name,
        issue->>'severity' AS severity,
        COUNT(*) AS count
      FROM data_quality_events,
        jsonb_array_elements(issues) AS issue
      WHERE checked_at > NOW() - INTERVAL '${hours} hours'
      GROUP BY check_name, severity
      ORDER BY count DESC
      LIMIT 5
    `);

    // Issues per location (top 5 problem locations)
    const topLocations = await pool.query(`
      SELECT
        location_name,
        COUNT(*) AS check_count,
        SUM(issues_count) AS total_issues,
        AVG(quality_score)::int AS avg_score
      FROM data_quality_events
      WHERE checked_at > NOW() - INTERVAL '${hours} hours'
        AND issues_count > 0
      GROUP BY location_name
      ORDER BY total_issues DESC
      LIMIT 5
    `);

    const stats = overall.rows[0] || {};
    const total = parseInt(stats.total) || 0;
    const passed = parseInt(stats.passed_count) || 0;
    const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : "0";

    res.json({
      time_window_hours: hours,
      total_messages: total,
      passed: passed,
      failed: parseInt(stats.failed_count) || 0,
      warnings: parseInt(stats.warning_count) || 0,
      pass_rate: parseFloat(passRate),
      avg_score: parseInt(stats.avg_score) || 100,
      min_score: parseInt(stats.min_score) || 100,
      max_score: parseInt(stats.max_score) || 100,
      top_issues: topIssues.rows,
      top_problem_locations: topLocations.rows,
    });
  } catch (err) {
    console.error("Error fetching DQ stats:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// ═══════════════════════════════════════════════════════════
//  ENDPOINT 12: Recent DQ events (for the Data Quality page table)
// ═══════════════════════════════════════════════════════════
app.get("/api/data-quality/events", async (req, res) => {
  const hours = parseInt(req.query.hours) || 24;
  const onlyIssues = req.query.only_issues === "true";
  try {
    const result = await pool.query(`
      SELECT
        checked_at,
        location_name,
        quality_score,
        passed,
        issues_count,
        issues
      FROM data_quality_events
      WHERE checked_at > NOW() - INTERVAL '${hours} hours'
        ${onlyIssues ? "AND issues_count > 0" : ""}
      ORDER BY checked_at DESC
      LIMIT 100
    `);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching DQ events:", err.message);
    res.status(500).json({ error: err.message });
  }
});


// REMINDER: Don't forget to update the START SERVER console.log message
// to mention the new endpoints. See the bottom of this file.


// ═══════════════════════════════════════════════════════════
//  START SERVER
// ═══════════════════════════════════════════════════════════
app.listen(PORT, () => {
  console.log(`\n🚦 Traffic Dashboard API running on http://localhost:${PORT}`);
  console.log(`\n  Endpoints:`);
  console.log(`    GET /api/predictions/latest`);
  console.log(`    GET /api/anomalies?hours=24`);
  console.log(`    GET /api/aggregates?hours=24`);
  console.log(`    GET /api/weather/latest`);
  console.log(`    GET /api/health`);
  console.log(`    GET /api/locations`);
  console.log(`    GET /api/speed-history/:location?hours=24`);
  console.log(`    GET /api/congestion-distribution?days=7`);
  console.log(`    GET /api/forecasts/latest                    [Phase C]`);
  console.log(`    GET /api/ai-summary/latest                   [Phase C]`);
  console.log(`    GET /api/data-quality/stats?hours=24         [Phase C]`);
  console.log(`    GET /api/data-quality/events?hours=24        [Phase C]`);
  console.log(`\n  Waiting for requests...\n`);
});