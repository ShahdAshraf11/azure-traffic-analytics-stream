import { TrendingDown, TrendingUp, Minus, Clock, Info } from "lucide-react";
import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";

const API = "http://localhost:5000/api";

interface ForecastHorizon {
  predicted_speed: number;
  predicted_class: string;
  confidence: number;
  target_time: string;
  forecast_made_at: string;
}

interface LocationForecast {
  location_name: string;
  current_speed: number;
  free_flow_speed: number;
  forecasts: {
    "20min"?: ForecastHorizon;
    "30min"?: ForecastHorizon;
    "60min"?: ForecastHorizon;
  } | null;
}

/**
 * Forecasts Page
 * ──────────────
 * Full table view of all 25 monitored locations × 3 forecast horizons (20/30/60 min).
 * Auto-refreshes every 60 seconds.
 *
 * Reads from: GET /api/forecasts/latest
 */
export default function Forecasts() {
  const [data, setData] = useState<LocationForecast[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"name" | "drop" | "current">("drop");

  useEffect(() => {
    const fetchForecasts = () => {
      fetch(`${API}/forecasts/latest`)
        .then((r) => r.json())
        .then((rows) => {
          if (Array.isArray(rows)) setData(rows);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    };
    fetchForecasts();
    const interval = setInterval(fetchForecasts, 60_000);
    return () => clearInterval(interval);
  }, []);

  // Compute drop for sorting
  const enriched = data.map((d) => {
    const future = d.forecasts?.["60min"]?.predicted_speed ?? d.current_speed;
    return { ...d, drop: d.current_speed - future };
  });

  // Sort
  const sorted = [...enriched].sort((a, b) => {
    if (sortBy === "name") return a.location_name.localeCompare(b.location_name);
    if (sortBy === "current") return b.current_speed - a.current_speed;
    return b.drop - a.drop;
  });

  // ── Helpers ──
  const getTrendIcon = (drop: number) => {
    if (drop > 5) return <TrendingDown className="w-4 h-4 text-traffic-severe" />;
    if (drop < -5) return <TrendingUp className="w-4 h-4 text-traffic-free" />;
    return <Minus className="w-4 h-4 text-muted-foreground" />;
  };

  const getClassColor = (cls: string) => {
    if (cls === "Closed" || cls === "Severe") return "text-traffic-severe";
    if (cls === "Heavy") return "text-traffic-heavy";
    if (cls === "Moderate") return "text-traffic-moderate";
    return "text-traffic-free";
  };

  const getClassBg = (cls: string) => {
    if (cls === "Closed" || cls === "Severe") return "bg-traffic-severe/10";
    if (cls === "Heavy") return "bg-traffic-heavy/10";
    if (cls === "Moderate") return "bg-traffic-moderate/10";
    return "bg-traffic-free/10";
  };

  const totalWithForecasts = data.filter((d) => d.forecasts).length;
  const totalLocations = data.length;
  const warmupPct = totalLocations > 0
    ? Math.round((totalWithForecasts / totalLocations) * 100)
    : 0;

  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Traffic Forecasts</h1>
            <p className="text-sm text-muted-foreground mt-1">
              ML-powered predictions for the next 20, 30, and 60 minutes
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Auto-refresh every 60s</span>
          </div>
        </div>

        {/* Warm-up info banner */}
        {warmupPct < 100 && (
          <div className="bg-card border border-border rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-primary mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="text-xs text-foreground font-medium">
                  Forecast warm-up: {warmupPct}% ({totalWithForecasts}/{totalLocations} locations)
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Each location needs ~145 readings (~12 hours of data) before forecasts become available.
                  Locations without forecasts are marked with —.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Sort controls */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Sort by:</span>
          {(["drop", "name", "current"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSortBy(s)}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                sortBy === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-muted-foreground hover:bg-accent"
              }`}
            >
              {s === "drop" ? "Predicted drop" : s === "name" ? "Name" : "Current speed"}
            </button>
          ))}
        </div>

        {/* Forecast table */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-surface-0 border-b border-border">
              <tr className="text-muted-foreground">
                <th className="text-left p-3 font-medium">Location</th>
                <th className="text-right p-3 font-medium">Current</th>
                <th className="text-right p-3 font-medium">Free Flow</th>
                <th className="text-center p-3 font-medium">+20 min</th>
                <th className="text-center p-3 font-medium">+30 min</th>
                <th className="text-center p-3 font-medium">+60 min</th>
                <th className="text-center p-3 font-medium">Trend</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-muted-foreground">
                    Loading forecasts...
                  </td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-muted-foreground">
                    No forecasts yet. Run the consumer for ~12 hours to warm up the forecast buffers.
                  </td>
                </tr>
              ) : (
                sorted.map((row) => {
                  const f20 = row.forecasts?.["20min"];
                  const f30 = row.forecasts?.["30min"];
                  const f60 = row.forecasts?.["60min"];
                  return (
                    <tr key={row.location_name} className="border-t border-border hover:bg-accent/30">
                      <td className="p-3 text-foreground font-medium">
                        {row.location_name}
                      </td>
                      <td className="p-3 text-right text-foreground">
                        {row.current_speed?.toFixed(0)} km/h
                      </td>
                      <td className="p-3 text-right text-muted-foreground">
                        {row.free_flow_speed?.toFixed(0)} km/h
                      </td>
                      <td className="p-3 text-center">
                        {f20 ? (
                          <div className={`inline-flex flex-col items-center px-2 py-1 rounded ${getClassBg(f20.predicted_class)}`}>
                            <span className={`font-semibold ${getClassColor(f20.predicted_class)}`}>
                              {f20.predicted_speed.toFixed(0)} km/h
                            </span>
                            <span className="text-[9px] text-muted-foreground">
                              {f20.predicted_class}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        {f30 ? (
                          <div className={`inline-flex flex-col items-center px-2 py-1 rounded ${getClassBg(f30.predicted_class)}`}>
                            <span className={`font-semibold ${getClassColor(f30.predicted_class)}`}>
                              {f30.predicted_speed.toFixed(0)} km/h
                            </span>
                            <span className="text-[9px] text-muted-foreground">
                              {f30.predicted_class}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        {f60 ? (
                          <div className={`inline-flex flex-col items-center px-2 py-1 rounded ${getClassBg(f60.predicted_class)}`}>
                            <span className={`font-semibold ${getClassColor(f60.predicted_class)}`}>
                              {f60.predicted_speed.toFixed(0)} km/h
                            </span>
                            <span className="text-[9px] text-muted-foreground">
                              {f60.predicted_class}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        <div className="flex justify-center">
                          {row.forecasts ? getTrendIcon(row.drop) : (
                            <span className="text-muted-foreground text-[10px]">—</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

      </div>
    </DashboardLayout>
  );
}
