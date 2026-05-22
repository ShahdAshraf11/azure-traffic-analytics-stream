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
