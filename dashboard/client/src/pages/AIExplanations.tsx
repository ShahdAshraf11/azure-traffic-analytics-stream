import { DashboardLayout } from "@/components/DashboardLayout";
import { ROADS, getCongestionTailwind, getCongestionBg } from "@/data/mockData";
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, CartesianGrid, Tooltip } from "recharts";

export default function AIExplanations() {
  const [selected, setSelected] = useState(ROADS[0]);

  const shapData = selected.shapFeatures.map((f) => ({
    feature: f.feature,
    value: f.value,
    fill: f.positive ? "hsl(0,84%,60%)" : "hsl(142,71%,45%)",
  }));

  return (
    <DashboardLayout>
      <div className="p-4 space-y-4">
        <h2 className="text-lg font-bold text-foreground">AI Explanations</h2>

        <div className="grid grid-cols-[250px_1fr] gap-4">
          {/* Road selector */}
          <div className="space-y-2">
            {ROADS.filter(r => r.shapFeatures.length > 0).map((road) => (
              <button
                key={road.id}
                onClick={() => setSelected(road)}
                className={`w-full text-left p-3 rounded-lg border transition-all text-xs ${
                  selected.id === road.id
                    ? "bg-primary/10 border-primary"
                    : "bg-card border-border hover:border-primary/50"
                }`}
              >
                <p className="font-medium text-foreground">{road.name}</p>
                <p className={`text-[10px] ${getCongestionTailwind(road.congestion)}`}>{road.congestion} · {road.currentSpeed} km/h</p>
              </button>
            ))}
          </div>

          {/* Detail */}
          <div className="space-y-4">
            <div className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-sm font-semibold text-foreground">{selected.name}</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${getCongestionBg(selected.congestion)} text-foreground font-medium`}>
                  {selected.congestion}
                </span>
              </div>
              <div className="grid grid-cols-4 gap-4 text-xs">
                <div><p className="text-muted-foreground">Speed</p><p className="text-lg font-bold text-foreground">{selected.currentSpeed} km/h</p></div>
                <div><p className="text-muted-foreground">Free Flow</p><p className="text-lg font-bold text-foreground">{selected.freeFlowSpeed} km/h</p></div>
                <div><p className="text-muted-foreground">Confidence</p><p className="text-lg font-bold text-foreground">{(selected.confidence * 100).toFixed(0)}%</p></div>
                <div><p className="text-muted-foreground">Last Update</p><p className="text-lg font-bold text-foreground">{selected.lastUpdated}</p></div>
              </div>
            </div>

            {shapData.length > 0 && (
              <div className="bg-card rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold text-foreground mb-3">Feature Importance (SHAP)</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={shapData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
                      <XAxis type="number" tick={{ fontSize: 10, fill: "hsl(218,11%,65%)" }} />
                      <YAxis dataKey="feature" type="category" tick={{ fontSize: 9, fill: "hsl(218,11%,65%)" }} width={180} />
                      <Tooltip contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8, fontSize: 10 }} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {shapData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
