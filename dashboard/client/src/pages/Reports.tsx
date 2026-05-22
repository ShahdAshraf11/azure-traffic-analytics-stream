// import { FileText, Download } from "lucide-react";
// import { DashboardLayout } from "@/components/DashboardLayout";

// export default function Reports() {
//   return (
//     <DashboardLayout>
//       <div className="p-6 space-y-6">
//         <div>
//           <h1 className="text-2xl font-bold text-foreground">Reports</h1>
//           <p className="text-sm text-muted-foreground mt-1">
//             Traffic analysis reports and recommendations
//           </p>
//         </div>

//         {/* Recommendations Card */}
//         <div className="bg-card rounded-lg border border-border overflow-hidden">
//           <div className="p-6 border-b border-border">
//             <div className="flex items-start gap-4">
//               <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
//                 <FileText className="w-6 h-6 text-primary" />
//               </div>
//               <div className="flex-1">
//                 <h2 className="text-lg font-semibold text-foreground">
//                   Real-Time Traffic Analysis Report
//                 </h2>
//                 <p className="text-sm text-muted-foreground mt-1">
//                   Comprehensive analysis of Cairo traffic patterns with key findings 
//                   and 5 strategic recommendations for urban mobility improvement.
//                 </p>
//                 <div className="flex items-center gap-3 mt-4">
//                   <a
//                     href="/reports/traffic_Recommendations.pdf"
//                     target="_blank"
//                     rel="noopener noreferrer"
//                     className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition"
//                   >
//                     <FileText className="w-4 h-4" />
//                     View Report
//                   </a>
//                   <a
//                     href="/reports/traffic_Recommendations.pdf"
//                     download
//                     className="inline-flex items-center gap-2 px-4 py-2 bg-card border border-border text-foreground rounded-md text-sm font-medium hover:bg-accent transition"
//                   >
//                     <Download className="w-4 h-4" />
//                     Download
//                   </a>
//                 </div>
//               </div>
//             </div>
//           </div>

//           {/* Embedded PDF preview */}
//           <div className="p-4">
//             <iframe
//               src="/reports/traffic_Recommendations.pdf"
//               className="w-full h-[700px] border border-border rounded"
//               title="Traffic Recommendations Report"
//             />
//           </div>
//         </div>

//         {/* Key findings card */}
//         <div className="bg-card rounded-lg border border-border p-6">
//           <h3 className="text-base font-semibold text-foreground mb-3">
//             Key Findings at a Glance
//           </h3>
//           <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
//             <div className="bg-traffic-severe/10 rounded-lg p-3">
//               <p className="text-2xl font-bold text-traffic-severe">89.4%</p>
//               <p className="text-xs text-muted-foreground mt-1">
//                 Average congestion ratio at peak hour
//               </p>
//             </div>
//             <div className="bg-traffic-heavy/10 rounded-lg p-3">
//               <p className="text-2xl font-bold text-traffic-heavy">30 km/h</p>
//               <p className="text-xs text-muted-foreground mt-1">
//                 City-wide average speed
//               </p>
//             </div>
//             <div className="bg-primary/10 rounded-lg p-3">
//               <p className="text-2xl font-bold text-primary">5</p>
//               <p className="text-xs text-muted-foreground mt-1">
//                 Strategic recommendations
//               </p>
//             </div>
//           </div>
//         </div>
//       </div>
//     </DashboardLayout>
//   );
// }

import { FileText, Download, BarChart3, AlertTriangle, Activity, ShieldCheck, Printer, RefreshCw } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";

const API = "http://localhost:5000/api";

interface LocationLatest {
  location_name: string;
  current_speed: number;
  free_flow_speed: number;
  predicted_congestion: string;
  road_closure: boolean;
  lat: number;
  lon: number;
}

interface Anomaly {
  detected_at: string;
  location_name: string;
  reason: string;
}

interface DQStats {
  pass_rate: number;
  total_messages: number;
  warnings: number;
  failed: number;
}

interface AISummary {
  generated_at: string;
  summary_text: string;
}

export default function Reports() {
  const [locations, setLocations] = useState<LocationLatest[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [dq, setDQ] = useState<DQStats | null>(null);
  const [ai, setAI] = useState<AISummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const reportRef = useRef<HTMLDivElement>(null);

  const fetchAll = () => {
    Promise.all([
      fetch(`${API}/predictions/latest`).then((r) => r.json()),
      fetch(`${API}/anomalies`).then((r) => r.json()),
      fetch(`${API}/data-quality/stats?hours=24`).then((r) => r.json()),
      fetch(`${API}/ai-summary/latest`).then((r) => r.json()),
    ])
      .then(([locs, anoms, dqs, aiSum]) => {
        if (Array.isArray(locs)) setLocations(locs);
        if (Array.isArray(anoms)) setAnomalies(anoms.slice(0, 10));
        if (dqs) setDQ(dqs);
        if (aiSum && aiSum.summary_text) setAI(aiSum);
        setLastUpdated(new Date());
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 60_000);
    return () => clearInterval(interval);
  }, []);

  const handlePrint = () => window.print();

  // Aggregate metrics
  const closuresCount = locations.filter((l) => l.road_closure).length;
  const totalLocations = locations.length;
  const avgSpeed = locations.length > 0
    ? Math.round(locations.reduce((s, l) => s + (l.current_speed || 0), 0) / locations.length)
    : 0;
  const freeFlowCount = locations.filter((l) => l.predicted_congestion === "Free Flow").length;
  const severeCount = locations.filter((l) =>
    l.predicted_congestion === "Severe" ||
    l.predicted_congestion === "Closed" ||
    l.road_closure
  ).length;
  const freeFlowPct = totalLocations > 0 ? Math.round((freeFlowCount / totalLocations) * 100) : 0;

  // Worst 5 locations
  const worstFive = [...locations]
    .filter((l) => l.free_flow_speed > 0)
    .sort((a, b) => (a.current_speed / a.free_flow_speed) - (b.current_speed / b.free_flow_speed))
    .slice(0, 5);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-6">
          <div className="flex items-center gap-2 text-muted-foreground">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Generating report...</span>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        <div className="flex items-start justify-between print:hidden">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Reports</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Auto-generated reports from live system data
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchAll}
              className="inline-flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-md text-sm font-medium hover:bg-accent transition"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh Data
            </button>
            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition"
            >
              <Printer className="w-4 h-4" />
              Print / Save as PDF
            </button>
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border p-4 print:hidden">
          <h3 className="text-sm font-semibold text-foreground mb-3">Other Available Reports</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <a
              href="/reports/traffic_Recommendations.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-muted rounded-md hover:bg-accent transition"
            >
              <FileText className="w-5 h-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">
                  Cairo Traffic Analysis & Recommendations
                </p>
                <p className="text-xs text-muted-foreground">
                  Strategic findings · PDF
                </p>
              </div>
              <Download className="w-4 h-4 text-muted-foreground shrink-0" />
            </a>
          </div>
        </div>

        <div
          ref={reportRef}
          className="bg-card rounded-lg border border-border p-8 space-y-6 print:border-0 print:shadow-none print:p-0"
        >
          <div className="border-b border-border pb-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-primary tracking-wider">
                  CAIRO SMART TRAFFIC — LIVE SYSTEM REPORT
                </p>
                <h2 className="text-3xl font-bold text-foreground mt-2">
                  Operational Status Snapshot
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Auto-generated from live system data
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">GENERATED</p>
                <p className="text-sm font-medium text-foreground">
                  {lastUpdated.toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" })}
                </p>
                <p className="text-sm font-medium text-foreground">
                  {lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            </div>
          </div>

          {ai && (
            <div className="bg-primary/5 border-l-4 border-primary rounded p-4">
              <p className="text-xs font-medium text-primary tracking-wider mb-2">
                EXECUTIVE SUMMARY · AI-GENERATED
              </p>
              <p className="text-sm text-foreground leading-relaxed italic">
                "{ai.summary_text}"
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Generated by Gemini at {new Date(ai.generated_at).toLocaleTimeString()}
              </p>
            </div>
          )}

          <div>
            <h3 className="text-sm font-bold text-foreground tracking-wider mb-3">
              KEY METRICS
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-primary" />
                  <p className="text-xs text-muted-foreground">Locations Monitored</p>
                </div>
                <p className="text-3xl font-bold text-foreground">{totalLocations}</p>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="w-4 h-4 text-primary" />
                  <p className="text-xs text-muted-foreground">City Avg Speed</p>
                </div>
                <p className="text-3xl font-bold text-foreground">
                  {avgSpeed} <span className="text-base font-normal text-muted-foreground">km/h</span>
                </p>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-traffic-severe" />
                  <p className="text-xs text-muted-foreground">Severe / Closed</p>
                </div>
                <p className="text-3xl font-bold text-traffic-severe">{severeCount}</p>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldCheck className="w-4 h-4 text-traffic-free" />
                  <p className="text-xs text-muted-foreground">Free Flow %</p>
                </div>
                <p className="text-3xl font-bold text-traffic-free">{freeFlowPct}%</p>
              </div>
            </div>
          </div>

          {dq && (
            <div>
              <h3 className="text-sm font-bold text-foreground tracking-wider mb-3">
                DATA QUALITY (LAST 24H)
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-muted rounded p-3">
                  <p className="text-xs text-muted-foreground">Pass Rate</p>
                  <p className="text-xl font-bold text-traffic-free">{dq.pass_rate?.toFixed(1) || 0}%</p>
                </div>
                <div className="bg-muted rounded p-3">
                  <p className="text-xs text-muted-foreground">Messages Checked</p>
                  <p className="text-xl font-bold text-foreground">{dq.total_messages || 0}</p>
                </div>
                <div className="bg-muted rounded p-3">
                  <p className="text-xs text-muted-foreground">Warnings</p>
                  <p className="text-xl font-bold text-traffic-moderate">{dq.warnings || 0}</p>
                </div>
              </div>
            </div>
          )}

          {worstFive.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-foreground tracking-wider mb-3">
                MOST CONGESTED LOCATIONS RIGHT NOW
              </h3>
              <table className="w-full text-sm">
                <thead className="border-b border-border">
                  <tr className="text-muted-foreground">
                    <th className="text-left py-2 font-medium">Location</th>
                    <th className="text-left py-2 font-medium">Predicted Class</th>
                    <th className="text-right py-2 font-medium">Current</th>
                    <th className="text-right py-2 font-medium">Free Flow</th>
                    <th className="text-right py-2 font-medium">Ratio</th>
                  </tr>
                </thead>
                <tbody>
                  {worstFive.map((loc) => {
                    const ratio = loc.free_flow_speed > 0
                      ? Math.round((loc.current_speed / loc.free_flow_speed) * 100)
                      : 0;
                    return (
                      <tr key={loc.location_name} className="border-b border-border">
                        <td className="py-2 text-foreground">{loc.location_name}</td>
                        <td className="py-2 text-muted-foreground">{loc.predicted_congestion}</td>
                        <td className="py-2 text-right text-foreground tabular-nums">
                          {loc.current_speed} km/h
                        </td>
                        <td className="py-2 text-right text-muted-foreground tabular-nums">
                          {loc.free_flow_speed} km/h
                        </td>
                        <td className="py-2 text-right tabular-nums">
                          <span className={ratio < 50 ? "text-traffic-severe font-medium" : "text-foreground"}>
                            {ratio}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {anomalies.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-foreground tracking-wider mb-3">
                RECENT ANOMALIES
              </h3>
              <div className="space-y-2">
                {anomalies.slice(0, 5).map((a, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 bg-muted rounded">
                    <AlertTriangle className="w-4 h-4 text-traffic-severe shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{a.location_name}</p>
                      <p className="text-xs text-muted-foreground">{a.reason}</p>
                    </div>
                    <p className="text-xs text-muted-foreground shrink-0">
                      {a.detected_at && new Date(a.detected_at).toLocaleTimeString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </DashboardLayout>
  );
}
