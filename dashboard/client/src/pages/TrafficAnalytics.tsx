import { DashboardLayout } from "@/components/DashboardLayout";
import { SPEED_OVER_TIME, CONGESTION_DISTRIBUTION } from "@/data/mockData";
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Legend,
} from "recharts";

const weatherImpact = Array.from({ length: 30 }, () => ({
  rain: Math.random() * 10,
  congestion: 20 + Math.random() * 60,
}));

export default function TrafficAnalytics() {
  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        <h2 className="text-lg font-bold text-foreground">Traffic Analytics</h2>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Speed Over Time (24h)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={SPEED_OVER_TIME}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
                  <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8 }} />
                  <Legend />
                  <Line type="monotone" dataKey="ringRoad" stroke="hsl(217,91%,60%)" strokeWidth={2} dot={false} name="Ring Road" />
                  <Line type="monotone" dataKey="salahSalem" stroke="hsl(0,84%,60%)" strokeWidth={2} dot={false} name="Salah Salem" />
                  <Line type="monotone" dataKey="october" stroke="hsl(48,96%,53%)" strokeWidth={2} dot={false} name="6th of Oct." />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Congestion Distribution</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={CONGESTION_DISTRIBUTION}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
                  <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "hsl(218,11%,65%)" }} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8 }} />
                  <Legend />
                  <Bar dataKey="free" stackId="a" fill="hsl(142,71%,45%)" name="Free" />
                  <Bar dataKey="moderate" stackId="a" fill="hsl(48,96%,53%)" name="Moderate" />
                  <Bar dataKey="heavy" stackId="a" fill="hsl(25,95%,53%)" name="Heavy" />
                  <Bar dataKey="severe" stackId="a" fill="hsl(0,84%,60%)" name="Severe" />
                  <Bar dataKey="closed" stackId="a" fill="hsl(220,9%,46%)" name="Closed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-card rounded-lg border border-border p-4 col-span-2">
            <h3 className="text-sm font-semibold text-foreground mb-3">Weather Impact — Rain vs Congestion</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
                  <XAxis dataKey="rain" name="Rain (mm)" tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <YAxis dataKey="congestion" name="Congestion %" tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                  <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8 }} />
                  <Scatter data={weatherImpact} fill="hsl(217,91%,60%)" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
