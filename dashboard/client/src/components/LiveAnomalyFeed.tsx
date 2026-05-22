import { ANOMALIES } from "@/data/mockData";
import { LineChart, Line, ResponsiveContainer } from "recharts";

export function LiveAnomalyFeed() {
  return (
    <div className="bg-card rounded-lg border border-border p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Live Anomaly Feed</h3>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-destructive animate-pulse-dot" />
          <span className="text-[10px] font-medium text-destructive">LIVE</span>
        </div>
      </div>

      <div className="flex gap-2 mb-3">
        <select className="text-[10px] bg-accent border border-border rounded px-2 py-1 text-foreground">
          <option>Last 1 Hour</option>
          <option>Last 6 Hours</option>
          <option>Last 24 Hours</option>
        </select>
        <select className="text-[10px] bg-accent border border-border rounded px-2 py-1 text-foreground">
          <option>All Locations</option>
        </select>
        <select className="text-[10px] bg-accent border border-border rounded px-2 py-1 text-foreground">
          <option>All Severity</option>
        </select>
      </div>

      <div className="flex-1 space-y-2 overflow-auto">
        {ANOMALIES.map((a) => (
          <div key={a.id} className="bg-accent/50 rounded-lg p-2.5 border border-border">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-destructive text-destructive-foreground">
                  ANOMALY
                </span>
                <span className="text-xs font-medium text-foreground">{a.road}</span>
              </div>
              <span className="text-[10px] text-muted-foreground">{a.time}</span>
            </div>
            <p className="text-[10px] text-muted-foreground mb-1">
              {a.currentSpeed} km/h / {a.freeFlowSpeed} km/h · Score: {a.score.toFixed(2)}
            </p>
            <p className="text-[10px] text-muted-foreground mb-1">{a.reason}</p>
            <div className="h-8">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={a.speedHistory.map((v, i) => ({ i, v }))}>
                  <Line type="monotone" dataKey="v" stroke="hsl(0, 84%, 60%)" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>

      <button className="text-xs text-primary hover:underline mt-2 text-right">
        View All Anomalies →
      </button>
    </div>
  );
}
