import { BarChart3, Download, ZoomIn, X, AlertCircle } from "lucide-react";
import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";

// ─────────────────────────────────────────────────────────────────────────
// POWER BI EMBED CONFIGURATION
// ─────────────────────────────────────────────────────────────────────────
// This is the "Secure embed" URL (Embed report → Website or portal).
// Requires viewers to be signed in to Power BI with access to the report.
// During your demo on your own machine where you're signed in, this works.
// For evaluators viewing later without sign-in, the screenshot gallery below
// always works.
// ─────────────────────────────────────────────────────────────────────────

const POWERBI_EMBED_URL = "https://app.powerbi.com/reportEmbed?reportId=2ba935d1-5816-4599-9777-20022af4008f&autoAuth=true&ctid=f816351e-812c-4687-b556-55e4cacc1859";

// ─────────────────────────────────────────────────────────────────────────
// SCREENSHOTS (always shown alongside the embed)
// ─────────────────────────────────────────────────────────────────────────
// Add screenshots to dashboard/client/public/powerbi/

interface Screenshot {
  filename: string;
  title: string;
  description?: string;
}

const SCREENSHOTS: Screenshot[] = [
  {
    filename: "dashboard1.png",
    title: "Main Dashboard View",
    description: "Executive overview with KPI cards, geographic map, district analysis"
  },
  {
    filename: "dashboard2.png",
    title: "Geographic Analysis",
    description: "Cairo locations color-coded by speed and congestion level"
  },
  {
    filename: "dashboard3.png",
    title: "Top Locations & District Comparison",
    description: "Bar chart of worst congestion areas"
  },
];

// ─────────────────────────────────────────────────────────────────────────
export default function PowerBIReports() {
  const [zoomed, setZoomed] = useState<Screenshot | null>(null);

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Power BI Reports</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Executive analytics and historical traffic intelligence
            </p>
          </div>
          <a
            href="/powerbi/traffic_data_bi.pbix"
            download
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition"
          >
            <Download className="w-4 h-4" />
            Download .pbix
          </a>
        </div>

        {/* Description Card */}
        <div className="bg-card rounded-lg border border-border p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <BarChart3 className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-foreground">
                Traffic Intelligence Dashboard
              </h2>
             
              <div className="flex flex-wrap gap-2 mt-3">
                {[
                  "Top 10 by Speed",
                  "District Comparison",
                  "Geographic Map",
                  "Congestion vs Free Flow",
                  "Peak Hour Analysis",
                ].map((page) => (
                  <span
                    key={page}
                    className="text-xs px-2 py-1 bg-primary/10 text-primary rounded"
                  >
                    {page}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ─── EMBEDDED LIVE REPORT ─── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-foreground">Live Interactive Report</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Requires Power BI sign-in</span>
            </div>
          </div>

          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <div className="relative w-full" style={{ paddingBottom: "47.5%" /* 1140:541 aspect */ }}>
              <iframe
                title="Power BI — Cairo Traffic Dashboard"
                src={POWERBI_EMBED_URL}
                frameBorder="0"
                allowFullScreen={true}
                className="absolute inset-0 w-full h-full"
              />
            </div>
          </div>
        </div>

        {/* ─── SCREENSHOT GALLERY (always visible as fallback) ─── */}
        {SCREENSHOTS.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-foreground">Dashboard Preview Gallery</h3>
              <p className="text-xs text-muted-foreground italic">Click any image to enlarge</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {SCREENSHOTS.map((shot) => (
                <div
                  key={shot.filename}
                  className="bg-card rounded-lg border border-border overflow-hidden group cursor-pointer hover:border-primary transition"
                  onClick={() => setZoomed(shot)}
                >
                  <div className="relative">
                    <img
                      src={`/powerbi/${shot.filename}`}
                      alt={shot.title}
                      className="w-full h-auto"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                      <div className="bg-white rounded-full p-3">
                        <ZoomIn className="w-6 h-6 text-foreground" />
                      </div>
                    </div>
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-medium text-foreground">{shot.title}</p>
                    {shot.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{shot.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      
      </div>

      {/* Zoom modal */}
      {zoomed && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8 cursor-pointer"
          onClick={() => setZoomed(null)}
        >
          <button
            className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white flex items-center justify-center hover:bg-muted transition"
            onClick={() => setZoomed(null)}
          >
            <X className="w-5 h-5" />
          </button>
          <div className="max-w-7xl max-h-full">
            <img
              src={`/powerbi/${zoomed.filename}`}
              alt={zoomed.title}
              className="max-w-full max-h-[90vh] object-contain"
            />
            <p className="text-white text-center mt-4 font-medium">{zoomed.title}</p>
            {zoomed.description && (
              <p className="text-white/70 text-center text-sm mt-1">{zoomed.description}</p>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
