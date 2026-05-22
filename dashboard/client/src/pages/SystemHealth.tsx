import { DashboardLayout } from "@/components/DashboardLayout";
import { ROADS, SYSTEM_HEALTH, PREDICTION_ACCURACY } from "@/data/mockData";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, CartesianGrid, Tooltip } from "recharts";
import { CheckCircle, AlertCircle } from "lucide-react";

export default function SystemHealth() {
  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        <h2 className="text-lg font-bold text-foreground">System Health</h2>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Records Today", value: SYSTEM_HEALTH.recordsToday.toLocaleString() },
            { label: "API Success Rate", value: `${SYSTEM_HEALTH.apiSuccessRate}%` },
            { label: "Model Accuracy", value: `${SYSTEM_HEALTH.modelAccuracy}%` },
            { label: "Last Data", value: SYSTEM_HEALTH.lastDataReceived },
          ].map((m) => (
            <div key={m.label} className="bg-card rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p className="text-2xl font-bold text-foreground mt-1">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Data Freshness */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Data Freshness</h3>
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground border-b border-border">
                <th className="text-left pb-2">Location</th>
                <th className="text-left pb-2">Last Reading</th>
                <th className="text-left pb-2">Age</th>
                <th className="text-center pb-2">Status</th>
              </tr></thead>
              <tbody>
                {ROADS.slice(0, 10).map((r) => {
                  const age = Math.floor(Math.random() * 60);
                  return (
                    <tr key={r.id} className="border-b border-border">
                      <td className="py-2 text-foreground">{r.name}</td>
                      <td className="py-2 text-muted-foreground">{r.lastUpdated}</td>
                      <td className="py-2 text-muted-foreground">{age}s ago</td>
                      <td className="py-2 text-center">
                        {age < 45 ? (
                          <CheckCircle className="w-4 h-4 text-traffic-free inline" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-traffic-moderate inline" />
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Prediction Accuracy */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Prediction Accuracy by Class</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={PREDICTION_ACCURACY}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
                  <XAxis dataKey="level" tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8 }} />
                  <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                    {PREDICTION_ACCURACY.map((_, i) => {
                      const colors = ["hsl(142,71%,45%)", "hsl(48,96%,53%)", "hsl(25,95%,53%)", "hsl(0,84%,60%)", "hsl(220,9%,46%)"];
                      return <Cell key={i} fill={colors[i]} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
