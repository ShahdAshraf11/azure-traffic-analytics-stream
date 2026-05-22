import { TrendingDown, TrendingUp, Minus, AlertTriangle } from "lucide-react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

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
 * Forecast Preview Panel (shown on home page)
 * ────────────────────────────────────────────
 * Shows the top 5 locations where conditions are predicted to WORSEN
 * (biggest predicted speed drop in the next 60 min).
 *
 * Reads from: GET /api/forecasts/latest
 */
export function ForecastPreview() {
  const [data, setData] = useState<LocationForecast[]>([]);
  const [loading, setLoading] = useState(true);

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

  // ── Filter to locations with forecasts available ──
  const withForecasts = data.filter((d) => d.forecasts && d.forecasts["60min"]);

  // ── Sort by predicted speed drop (worst first) ──
  const worstFirst = [...withForecasts]
    .map((d) => {
      const future = d.forecasts?.["60min"]?.predicted_speed || d.current_speed;
      const drop = d.current_speed - future;
      return { ...d, drop };
    })
    .sort((a, b) => b.drop - a.drop)
    .slice(0, 5);

  // ── Empty state when forecasts aren't warm yet ──
  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-3">
        <h3 className="text-xs font-semibold mb-2">📊 Traffic Forecasts</h3>
        <p className="text-xs text-muted-foreground">Loading forecasts...</p>
      </div>
    );
  }

  if (worstFirst.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold">📊 Traffic Forecasts</h3>
        </div>
        <div className="flex items-start gap-2 text-xs text-muted-foreground">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <p className="leading-relaxed">
            Forecasts warming up. Need ~145 readings per location (about 12
            hours of data) before predictions become available.
          </p>
        </div>
      </div>
    );
  }

  // ── Helpers ──
  const getTrendIcon = (drop: number) => {
    if (drop > 5) return <TrendingDown className="w-3 h-3 text-traffic-severe" />;
    if (drop < -5) return <TrendingUp className="w-3 h-3 text-traffic-free" />;
    return <Minus className="w-3 h-3 text-muted-foreground" />;
  };

  const getClassColor = (cls: string) => {
    if (cls === "Closed") return "text-traffic-severe";
    if (cls === "Severe") return "text-traffic-severe";
    if (cls === "Heavy") return "text-traffic-heavy";
    if (cls === "Moderate") return "text-traffic-moderate";
    return "text-traffic-free";
  };

  return (
    <div className="bg-card rounded-lg border border-border p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold">
          📊 Forecasts <span className="text-muted-foreground font-normal">(Top 5 Worsening)</span>
        </h3>
        <Link
          to="/forecasts"
          className="text-[10px] text-primary hover:underline font-medium"
        >
          View all →
        </Link>
      </div>

      <table className="w-full text-[10px]">
        <thead>
          <tr className="text-muted-foreground">
            <th className="text-left pb-1.5 font-normal">Road</th>
            <th className="text-right pb-1.5 font-normal">Now</th>
            <th className="text-right pb-1.5 font-normal">+20m</th>
            <th className="text-right pb-1.5 font-normal">+60m</th>
            <th className="text-center pb-1.5 font-normal">Trend</th>
          </tr>
        </thead>
        <tbody>
          {worstFirst.map((row) => {
            const f20 = row.forecasts?.["20min"];
            const f60 = row.forecasts?.["60min"];
            return (
              <tr key={row.location_name} className="border-t border-border">
                <td className="py-1.5 text-foreground truncate max-w-[120px]">
                  {row.location_name}
                </td>
                <td className="py-1.5 text-right text-foreground">
                  {row.current_speed?.toFixed(0)}
                </td>
                <td className={`py-1.5 text-right ${getClassColor(f20?.predicted_class || "")}`}>
                  {f20?.predicted_speed?.toFixed(0) ?? "—"}
                </td>
                <td className={`py-1.5 text-right ${getClassColor(f60?.predicted_class || "")}`}>
                  {f60?.predicted_speed?.toFixed(0) ?? "—"}
                </td>
                <td className="py-1.5 text-center flex justify-center">
                  {getTrendIcon(row.drop)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
