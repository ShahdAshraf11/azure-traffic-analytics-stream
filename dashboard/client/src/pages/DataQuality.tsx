import { ShieldCheck, ShieldAlert, AlertTriangle, TrendingUp, Info } from "lucide-react";
import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";

const API = "http://localhost:5000/api";

interface DQStats {
  time_window_hours: number;
  total_messages: number;
  passed: number;
  failed: number;
  warnings: number;
  pass_rate: number;
  avg_score: number;
  min_score: number;
  max_score: number;
  top_issues: { check_name: string; severity: string; count: number }[];
  top_problem_locations: {
    location_name: string;
    check_count: number;
    total_issues: number;
    avg_score: number;
  }[];
}

interface DQEvent {
  checked_at: string;
  location_name: string;
  quality_score: number;
  passed: boolean;
  issues_count: number;
  issues: { check: string; severity: string; message: string }[];
}

/**
 * Data Quality Page
 * ─────────────────
 * Full DQ dashboard with overall stats, issue breakdown, problem locations,
 * and a recent events table.
 *
 * Reads from:
 *   GET /api/data-quality/stats?hours=24
 *   GET /api/data-quality/events?hours=24&only_issues=true
 */
export default function DataQuality() {
  const [stats, setStats] = useState<DQStats | null>(null);
  const [events, setEvents] = useState<DQEvent[]>([]);
  const [hours, setHours] = useState<24 | 6 | 1>(24);

  useEffect(() => {
    const fetchData = () => {
      fetch(`${API}/data-quality/stats?hours=${hours}`)
        .then((r) => r.json())
        .then(setStats)
        .catch(() => {});

      fetch(`${API}/data-quality/events?hours=${hours}&only_issues=true`)
        .then((r) => r.json())
        .then((rows) => {
          if (Array.isArray(rows)) setEvents(rows);
        })
        .catch(() => {});
    };
    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, [hours]);

  // ── Helpers ──
  const getSeverityColor = (sev: string) => {
    if (sev === "fatal" || sev === "critical") return "text-traffic-severe";
    if (sev === "warning") return "text-traffic-moderate";
    return "text-traffic-heavy";
  };

  const getSeverityBg = (sev: string) => {
    if (sev === "fatal" || sev === "critical") return "bg-traffic-severe/10";
    if (sev === "warning") return "bg-traffic-moderate/10";
    return "bg-traffic-heavy/10";
  };

  const getScoreColor = (score: number) => {
    if (score >= 95) return "text-traffic-free";
    if (score >= 80) return "text-traffic-moderate";
    if (score >= 50) return "text-traffic-heavy";
    return "text-traffic-severe";
  };

  const friendlyCheckName = (check: string) => {
    const names: Record<string, string> = {
      required_fields: "Missing required fields",
      speed_sanity: "Unrealistic speed values",
      free_flow_sanity: "Invalid free-flow speed",
      closure_consistency: "Closure flag inconsistencies",
      coordinates: "Coordinates outside Cairo",
      freshness: "Stale readings",
      weather_sanity: "Weather data issues",
    };
    return names[check] || check;
  };

  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Data Quality</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Validation results for incoming TomTom + OpenWeather data
            </p>
          </div>

          {/* Time window selector */}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground mr-2">Window:</span>
            {([1, 6, 24] as const).map((h) => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  hours === h
                    ? "bg-primary text-primary-foreground"
                    : "bg-card text-muted-foreground hover:bg-accent"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>

        {/* KPI cards */}
        {stats && (
          <div className="grid grid-cols-4 gap-3">
            {/* Pass rate */}
            <div className="bg-card rounded-lg p-3 flex items-center gap-3 border border-border">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                  stats.pass_rate >= 99 ? "bg-traffic-free/10" : "bg-traffic-moderate/10"
                }`}
              >
                {stats.pass_rate >= 99 ? (
                  <ShieldCheck className="w-5 h-5 text-traffic-free" />
                ) : (
                  <ShieldAlert className="w-5 h-5 text-traffic-moderate" />
                )}
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">Pass Rate</p>
                <p className="text-xl font-bold text-foreground">
                  {stats.pass_rate.toFixed(1)}%
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {stats.passed} / {stats.total_messages} messages
                </p>
              </div>
            </div>

            {/* Total checked */}
            <div className="bg-card rounded-lg p-3 flex items-center gap-3 border border-border">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Info className="w-5 h-5 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">Total Checked</p>
                <p className="text-xl font-bold text-foreground">{stats.total_messages}</p>
                <p className="text-[10px] text-muted-foreground">Last {hours}h</p>
              </div>
            </div>

            {/* Warnings */}
            <div className="bg-card rounded-lg p-3 flex items-center gap-3 border border-border">
              <div className="w-10 h-10 rounded-lg bg-traffic-moderate/10 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-traffic-moderate" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">Warnings</p>
                <p className="text-xl font-bold text-foreground">{stats.warnings}</p>
                <p className="text-[10px] text-muted-foreground">Passed with issues</p>
              </div>
            </div>

            {/* Failures */}
            <div className="bg-card rounded-lg p-3 flex items-center gap-3 border border-border">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                  stats.failed > 0 ? "bg-traffic-severe/10" : "bg-muted/30"
                }`}
              >
                <ShieldAlert
                  className={`w-5 h-5 ${
                    stats.failed > 0 ? "text-traffic-severe" : "text-muted-foreground"
                  }`}
                />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">Dropped</p>
                <p className="text-xl font-bold text-foreground">{stats.failed}</p>
                <p className="text-[10px] text-muted-foreground">Quality score &lt; 50</p>
              </div>
            </div>
          </div>
        )}

        {/* Two-column section: Top issues + Problem locations */}
        <div className="grid grid-cols-2 gap-3">
          {/* Top issues */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">
              Top Issues
            </h3>
            {stats && stats.top_issues.length > 0 ? (
              <div className="space-y-2">
                {stats.top_issues.map((issue, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span
                        className={`w-2 h-2 rounded-full ${getSeverityBg(issue.severity)} ${getSeverityColor(issue.severity)} bg-current`}
                      />
                      <span className="text-xs text-foreground truncate">
                        {friendlyCheckName(issue.check_name)}
                      </span>
                      <span
                        className={`text-[9px] uppercase tracking-wider ${getSeverityColor(issue.severity)}`}
                      >
                        {issue.severity}
                      </span>
                    </div>
                    <span className="text-xs font-semibold text-foreground tabular-nums">
                      {issue.count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No issues detected. All data passed quality checks.
              </p>
            )}
          </div>

          {/* Problem locations */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">
              Problem Locations
            </h3>
            {stats && stats.top_problem_locations.length > 0 ? (
              <div className="space-y-2">
                {stats.top_problem_locations.map((loc) => (
                  <div key={loc.location_name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-xs text-foreground truncate">
                        {loc.location_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="text-muted-foreground">
                        {loc.total_issues} issues
                      </span>
                      <span className={`font-semibold ${getScoreColor(loc.avg_score)}`}>
                        {loc.avg_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No problem locations.
              </p>
            )}
          </div>
        </div>

        {/* Recent issues table */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="p-4 border-b border-border">
            <h3 className="text-sm font-semibold text-foreground">
              Recent Issues
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Last 100 messages with quality issues (sorted newest first)
            </p>
          </div>
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-surface-0 border-b border-border sticky top-0">
                <tr className="text-muted-foreground">
                  <th className="text-left p-3 font-medium">Time</th>
                  <th className="text-left p-3 font-medium">Location</th>
                  <th className="text-center p-3 font-medium">Score</th>
                  <th className="text-left p-3 font-medium">Issues</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-muted-foreground">
                      No DQ issues in the last {hours}h.
                    </td>
                  </tr>
                ) : (
                  events.map((evt, i) => (
                    <tr key={i} className="border-t border-border hover:bg-accent/30">
                      <td className="p-3 text-muted-foreground tabular-nums">
                        {new Date(evt.checked_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </td>
                      <td className="p-3 text-foreground">{evt.location_name}</td>
                      <td className="p-3 text-center">
                        <span className={`font-semibold ${getScoreColor(evt.quality_score)}`}>
                          {evt.quality_score}
                        </span>
                      </td>
                      <td className="p-3 text-muted-foreground">
                        {evt.issues && evt.issues.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {evt.issues.map((issue, j) => (
                              <span
                                key={j}
                                className={`text-[10px] px-1.5 py-0.5 rounded ${getSeverityBg(issue.severity)} ${getSeverityColor(issue.severity)}`}
                                title={issue.message}
                              >
                                {friendlyCheckName(issue.check)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Help section */}
        <div className="bg-card rounded-lg border border-border p-3">
          <p className="text-[10px] font-medium text-muted-foreground tracking-wider mb-2">
            HOW IT WORKS
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Every incoming Kafka message is validated against 7 quality checks before reaching
            the ML pipeline. Messages with score &lt; 50 are dropped. Messages with score 50-79
            are flagged as warnings. Messages with score ≥ 80 pass cleanly.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
