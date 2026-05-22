import { AlertCircle, CheckCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";

const API = "http://localhost:5000/api";

export function RecentAlertsBar() {
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    const fetchAlerts = () => {
      fetch(`${API}/alerts?hours=1`)
        .then(r => r.json())
        .then(data => { if (Array.isArray(data)) setAlerts(data); })
        .catch(() => {});
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (alertType: string) => {
    if (alertType.startsWith("critical")) return "text-traffic-severe";
    if (alertType.startsWith("warning")) return "text-traffic-heavy";
    return "text-traffic-moderate";
  };

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-card border-b border-border text-xs overflow-hidden">
      <span className="font-semibold tracking-wider text-muted-foreground shrink-0">
        RECENT ALERTS
      </span>
      <div className="flex items-center gap-6 flex-1 min-w-0 overflow-hidden">
        {alerts.length > 0 ? (
          alerts.slice(0, 3).map((a, i) => (
            <div key={i} className="flex items-center gap-1.5 shrink-0">
              <AlertCircle className={`w-3.5 h-3.5 ${getSeverityColor(a.alert_type)}`} />
              <span className="text-foreground">{a.message?.slice(0, 80)}{a.message?.length > 80 ? "…" : ""}</span>
            </div>
          ))
        ) : (
          <div className="flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5 text-traffic-free" />
            <span className="text-foreground">No active alerts — all systems normal</span>
          </div>
        )}
      </div>
      <Link
        to="/anomalies"
        className="text-primary hover:underline shrink-0 font-medium"
      >
        View All Alerts
      </Link>
    </div>
  );
}
