import { useState, useEffect, useCallback } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { KPIBar } from "@/components/KPIBar";
import { TrafficMap } from "@/components/TrafficMap";
import { LiveAnomalyFeed } from "@/components/LiveAnomalyFeed";
import { BottomPanels } from "@/components/BottomPanels";
import { RoadDetailPopup } from "@/components/RoadDetailPopup";
import { fetchAndUpdateAll, type RoadData } from "@/data/mockData";
import { AISummaryBanner } from "@/components/AISummaryBanner";
import { ForecastPreview } from "@/components/ForecastPreview";

export default function Index() {
  const [selectedRoad, setSelectedRoad] = useState<RoadData | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);

  const refreshData = useCallback(async () => {
    await fetchAndUpdateAll();
    setRefreshKey((k) => k + 1);
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, [refreshData]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="animate-pulse text-2xl mb-2">◎</div>
            <p className="text-muted-foreground text-sm">Connecting to Traffic API...</p>
            <p className="text-muted-foreground text-xs mt-1">Make sure Express server is running on port 5000</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
  <DashboardLayout>
    <div className="p-3 flex flex-col gap-3" key={refreshKey}>
      {/* AI Summary Banner */}
      <AISummaryBanner />

      {/* Row 1: KPI Bar */}
      <KPIBar />

        {/* Row 2: Map + Right anomaly feed */}
        <div className="grid grid-cols-[1fr_320px] gap-3 h-[400px] min-h-0">
          {/* Center: Map */}
          <div className="relative rounded-lg overflow-hidden border border-border min-h-0">
            <TrafficMap onSelectRoad={setSelectedRoad} />
            {selectedRoad && (
              <div className="absolute top-4 right-4 z-[1000]">
                <RoadDetailPopup road={selectedRoad} onClose={() => setSelectedRoad(null)} />
              </div>
            )}
          </div>

          {/* Right: Forecast Preview + Anomaly Feed */}
          <div className="min-h-0 overflow-hidden flex flex-col gap-3">
            <ForecastPreview />
            <div className="flex-1 min-h-0 overflow-hidden">
              <LiveAnomalyFeed />
            </div>
          </div>
        </div>

        {/* Row 3: Bottom panels */}
        <BottomPanels />
      </div>
    </DashboardLayout>
  );
}
