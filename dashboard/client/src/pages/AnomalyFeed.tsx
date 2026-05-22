import { DashboardLayout } from "@/components/DashboardLayout";
import { useState, useEffect } from "react";
import { AlertTriangle, Shield, Construction, Activity, Globe } from "lucide-react";

const API = "http://localhost:5000/api";

interface AlertItem {
  type: "anomaly" | "alert";
  location: string;
  message: string;
  time: string;
  severity: string;
  speed?: number;
  freeFlow?: number;
  score?: number;
}

const severityConfig: Record<string, { color: string; bg: string; icon: any }> = {
  critical: { color: "text-traffic-severe", bg: "bg-traffic-severe", icon: AlertTriangle },
  warning: { color: "text-traffic-heavy", bg: "bg-traffic-heavy", icon: Shield },
  info: { color: "text-traffic-moderate", bg: "bg-traffic-moderate", icon: Activity },
  anomaly: { color: "text-destructive", bg: "bg-destructive", icon: Globe },
};

export default function AnomalyFeed() {
  const [items, setItems] = useState<AlertItem[]>([]);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [anomRes, alertRes] = await Promise.all([
          fetch(`${API}/anomalies?hours=${hours}`).then(r => r.json()).catch(() => []),
          fetch(`${API}/alerts?hours=${hours}`).then(r => r.json()).catch(() => []),
        ]);

        const combined: AlertItem[] = [];

        // Add anomalies (Isolation Forest detections)
        if (Array.isArray(anomRes)) {
          anomRes.forEach((a: any) => {
            combined.push({
              type: "anomaly",
              location: a.location_name || "Unknown",
              message: a.reason || "Unusual traffic pattern detected",
              time: a.detected_at ? new Date(a.detected_at).toLocaleString() : "—",
              severity: "anomaly",
              speed: a.current_speed,
              freeFlow: a.free_flow_speed,
              score: a.anomaly_score,
            });
          });
        }

        // Add alerts (AlertManager notifications)
        if (Array.isArray(alertRes)) {
          alertRes.forEach((a: any) => {
            const severity = a.alert_type?.split(":")[0] || "info";
            combined.push({
              type: "alert",
              location: a.location_name || "Unknown",
              message: a.message || "Alert triggered",
              time: a.triggered_at ? new Date(a.triggered_at).toLocaleString() : "—",
              severity,
            });
          });
        }

        // Sort by time (newest first)
        combined.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
        setItems(combined);
        setLoading(false);
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    };

    fetchAll();
    const interval = setInterval(fetchAll, 15000);
    return () => clearInterval(interval);
  }, [hours]);

  const timeButtons = [
    { label: "1 Hour", value: 1 },
    { label: "6 Hours", value: 6 },
    { label: "24 Hours", value: 24 },
    { label: "7 Days", value: 168 },
  ];

  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Alerts & Anomaly Feed</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Combined feed of AI anomaly detections and system alerts
            </p>
          </div>
          <div className="flex gap-2">
            {timeButtons.map((t) => (
              <button
                key={t.value}
                onClick={() => setHours(t.value)}
                className={`text-xs px-3 py-1.5 rounded-lg border border-border transition-all ${
                  hours === t.value
                    ? "bg-primary text-primary-foreground font-medium"
                    : "bg-accent text-muted-foreground hover:text-foreground"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-card rounded-lg border border-border p-3">
            <p className="text-[10px] text-muted-foreground">Total Items</p>
            <p className="text-xl font-bold text-foreground">{items.length}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-3">
            <p className="text-[10px] text-muted-foreground">AI Anomalies</p>
            <p className="text-xl font-bold text-destructive">{items.filter(i => i.type === "anomaly").length}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-3">
            <p className="text-[10px] text-muted-foreground">System Alerts</p>
            <p className="text-xl font-bold text-traffic-heavy">{items.filter(i => i.type === "alert").length}</p>
          </div>
        </div>

        {/* Feed */}
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading...</div>
        ) : items.length === 0 ? (
          <div className="bg-card rounded-lg border border-border p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-traffic-free/10 flex items-center justify-center mx-auto mb-3">
              <Shield className="w-6 h-6 text-traffic-free" />
            </div>
            <p className="text-sm font-semibold text-foreground">All Clear</p>
            <p className="text-xs text-muted-foreground mt-1">
              No anomalies or alerts in the last {hours === 168 ? "7 days" : `${hours} hours`}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item, idx) => {
              const cfg = severityConfig[item.severity] || severityConfig.info;
              const Icon = cfg.icon;
              return (
                <div
                  key={idx}
                  className="bg-card rounded-lg border border-border p-3 flex items-start gap-3 hover:border-border/80 transition-colors"
                >
                  {/* Severity badge */}
                  <div className="shrink-0 mt-0.5">
                    <span className={`inline-flex items-center gap-1 text-[9px] font-bold px-2 py-1 rounded ${cfg.bg} text-white`}>
                      <Icon className="w-3 h-3" />
                      {item.type === "anomaly" ? "ANOMALY" : item.severity.toUpperCase()}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-foreground">{item.location}</h3>
                      <span className="text-[10px] text-muted-foreground shrink-0 ml-2">{item.time}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{item.message}</p>
                    {item.speed !== undefined && (
                      <div className="flex gap-4 mt-1.5 text-[10px] text-muted-foreground">
                        <span>Speed: <b className="text-foreground">{item.speed} km/h</b></span>
                        <span>Free Flow: <b className="text-foreground">{item.freeFlow} km/h</b></span>
                        {item.score !== undefined && (
                          <span>Score: <b className="text-foreground">{item.score}</b></span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
