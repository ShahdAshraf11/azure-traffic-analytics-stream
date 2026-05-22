import { Map, AlertTriangle, TrendingUp, CloudRain } from "lucide-react";
import { ROADS, WEATHER, ANOMALIES } from "@/data/mockData";

export function KPIBar() {
  // Read data INSIDE the component so it picks up updates on every re-render
  const avgRatio = ROADS.length > 0
    ? Math.round(ROADS.reduce((sum, r) => sum + (r.freeFlowSpeed > 0 ? r.currentSpeed / r.freeFlowSpeed : 0), 0) / ROADS.length * 100)
    : 0;

  const kpis = [
    {
      icon: Map,
      label: "Total Roads Monitored",
      value: ROADS.length.toString(),
      sub: "100% Active",
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      icon: AlertTriangle,
      label: "Current Anomalies",
      value: ANOMALIES.length.toString(),
      sub: ANOMALIES.length > 0 ? "↑ vs last hour" : "All clear",
      color: ANOMALIES.length > 0 ? "text-traffic-severe" : "text-traffic-free",
      bg: ANOMALIES.length > 0 ? "bg-traffic-severe/10" : "bg-traffic-free/10",
    },
    {
      icon: TrendingUp,
      label: "Avg. Congestion Ratio",
      value: `${avgRatio}%`,
      sub: avgRatio >= 75 ? "Free Flow" : avgRatio >= 50 ? "Moderate" : "Congested",
      color: avgRatio >= 75 ? "text-traffic-free" : avgRatio >= 50 ? "text-traffic-moderate" : "text-traffic-heavy",
      bg: avgRatio >= 75 ? "bg-traffic-free/10" : avgRatio >= 50 ? "bg-traffic-moderate/10" : "bg-traffic-heavy/10",
    },
    {
      icon: CloudRain,
      label: "Current Weather",
      value: WEATHER.temperature ? `${WEATHER.temperature}°C` : "—",
      sub: WEATHER.condition || "Loading...",
      color: "text-primary",
      bg: "bg-primary/10",
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="bg-card rounded-lg p-3 flex items-center gap-3 border border-border">
          <div className={`w-10 h-10 rounded-lg ${kpi.bg} flex items-center justify-center shrink-0`}>
            <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
          </div>
          <div className="min-w-0">
            <p className="text-[10px] text-muted-foreground truncate">{kpi.label}</p>
            <p className="text-xl font-bold text-foreground">{kpi.value}</p>
            <p className="text-[10px] text-muted-foreground">{kpi.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
