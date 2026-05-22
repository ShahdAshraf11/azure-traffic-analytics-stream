import { SYSTEM_HEALTH, PREDICTION_ACCURACY } from "@/data/mockData";
import { Database, Cpu, Server, Monitor, ArrowRight, Network } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip, LabelList } from "recharts";
import { useState, useEffect } from "react";

const pipelineSteps = [
  { name: "Traffic\nAPIs", icon: Network, status: "Operational" },
  { name: "Kafka", icon: Server, status: "Operational" },
  { name: "AI Models", icon: Cpu, status: "Operational" },
  { name: "PostgreSQL", icon: Database, status: "Operational" },
  { name: "Dashboard", icon: Monitor, status: "Operational" },
];

const barColors = ["hsl(217,91%,60%)", "hsl(48,96%,53%)", "hsl(25,95%,53%)", "hsl(0,84%,60%)", "hsl(220,9%,46%)"];

export function SystemPipelineBar() {
  // Force re-render every 30s to pick up updated data
  const [, setTick] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setTick(t => t + 1), 30000);
    return () => clearInterval(i);
  }, []);
  // Read data INSIDE the component so it updates on re-render
  const stats = [
    { label: "Records Today", value: SYSTEM_HEALTH.recordsToday.toLocaleString(), change: SYSTEM_HEALTH.recordsChange, sub: "vs yesterday" },
    { label: "API Success Rate", value: `${SYSTEM_HEALTH.apiSuccessRate}%`, change: SYSTEM_HEALTH.apiChange, sub: "vs yesterday" },
    { label: "Model Accuracy", value: `${SYSTEM_HEALTH.modelAccuracy}%`, change: SYSTEM_HEALTH.accuracyChange, sub: "vs yesterday" },
    { label: "Last Data Received", value: SYSTEM_HEALTH.lastDataReceived, change: null, sub: "5 sec ago" },
  ];

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-2 items-stretch w-full min-w-0">
      {/* Pipeline */}
      <div className="bg-card rounded-lg border border-border p-3">
        <h3 className="text-xs font-semibold text-foreground mb-3">System Pipeline Health</h3>
        <div className="flex items-center justify-between gap-1">
          {pipelineSteps.map((step, i) => (
            <div key={step.name} className="flex items-center gap-1 flex-1">
              <div className="flex-1 flex flex-col items-center">
                <div className="w-full border border-border rounded-md px-2 py-2 flex items-center gap-2 bg-card">
                  <div className="w-8 h-8 rounded-md bg-accent flex items-center justify-center shrink-0">
                    <step.icon className="w-4 h-4 text-foreground" />
                  </div>
                  <span className="text-[10px] text-foreground leading-tight whitespace-pre-line font-medium">
                    {step.name}
                  </span>
                </div>
                <div className="flex items-center gap-1 mt-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-traffic-free" />
                  <span className="text-[9px] text-traffic-free">{step.status}</span>
                </div>
              </div>
              {i < pipelineSteps.length - 1 && (
                <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 -mt-4" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="bg-card rounded-lg border border-border flex">
        {stats.map((m, i) => (
          <div
            key={m.label}
            className={`px-3 py-2.5 flex flex-col justify-center min-w-[110px] ${
              i < stats.length - 1 ? "border-r border-border" : ""
            }`}
          >
            <p className="text-[10px] text-muted-foreground">{m.label}</p>
            <p className="text-lg font-bold text-foreground mt-0.5 leading-tight">{m.value}</p>
            {m.change !== null ? (
              <div className="flex items-center gap-1 mt-0.5">
                <span className={`text-[10px] font-medium ${m.change > 0 ? "text-traffic-free" : "text-traffic-severe"}`}>
                  {m.change > 0 ? "↑" : "↓"} {Math.abs(m.change)}%
                </span>
                <span className="text-[9px] text-muted-foreground">{m.sub}</span>
              </div>
            ) : (
              <p className="text-[10px] text-traffic-free mt-0.5">● {m.sub}</p>
            )}
          </div>
        ))}
      </div>

      {/* Prediction Accuracy */}
      <div className="w-44 bg-card rounded-lg border border-border p-2.5">
        <h4 className="text-[10px] font-semibold text-foreground mb-1">
          Prediction Accuracy <span className="text-muted-foreground font-normal">(Last 7 Days)</span>
        </h4>
        <div className="h-24">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={PREDICTION_ACCURACY.map(p => ({...p}))} margin={{ top: 12, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="level" tick={{ fontSize: 8, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 7, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} width={28} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8, fontSize: 9 }} />
              <Bar dataKey="accuracy" radius={[2, 2, 0, 0]}>
                <LabelList dataKey="accuracy" position="top" fill="hsl(220,13%,91%)" fontSize={8} formatter={(v: number) => `${v}%`} />
                {PREDICTION_ACCURACY.map((_, i) => (
                  <Cell key={i} fill={barColors[i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
