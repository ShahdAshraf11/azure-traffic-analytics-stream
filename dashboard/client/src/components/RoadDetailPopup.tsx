import type { RoadData } from "@/data/mockData";
import { getCongestionTailwind, getCongestionBg } from "@/data/mockData";
import { X, Thermometer, Droplets, Wind } from "lucide-react";
import { WEATHER } from "@/data/mockData";

interface RoadDetailPopupProps {
  road: RoadData;
  onClose: () => void;
}

export function RoadDetailPopup({ road, onClose }: RoadDetailPopupProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-4 w-72 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{road.name}</h3>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${getCongestionBg(road.congestion)} text-foreground`}>
            {road.congestion}
          </span>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-[10px] text-muted-foreground">Current Speed</p>
          <p className={`text-lg font-bold ${getCongestionTailwind(road.congestion)}`}>{road.currentSpeed} km/h</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground">Free Flow Speed</p>
          <p className="text-lg font-bold text-foreground">{road.freeFlowSpeed} km/h</p>
        </div>
      </div>

      <div className="mb-3">
        <p className="text-[10px] text-muted-foreground mb-1">Confidence</p>
        <div className="w-full h-2 bg-accent rounded-full overflow-hidden">
          <div
            className="h-full bg-traffic-free rounded-full"
            style={{ width: `${road.confidence * 100}%` }}
          />
        </div>
        <p className="text-[10px] text-right text-muted-foreground mt-0.5">{(road.confidence * 100).toFixed(0)}%</p>
      </div>

      {road.shapFeatures.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-semibold text-foreground mb-1.5">WHY?</h4>
          <div className="space-y-1">
            {road.shapFeatures.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className={`w-1.5 h-1.5 rounded-full ${f.positive ? "bg-traffic-severe" : "bg-traffic-free"}`} />
                <span className={f.positive ? "text-traffic-severe" : "text-traffic-free"}>{f.feature}</span>
                <span className="ml-auto text-muted-foreground">
                  {f.value > 0 ? "+" : ""}{f.value.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10px] text-muted-foreground border-t border-border pt-2">
        <p>Last Updated: {road.lastUpdated}</p>
      </div>

      <div className="flex items-center gap-3 mt-2 text-[9px] text-muted-foreground border-t border-border pt-2">
        <div className="flex items-center gap-1"><Thermometer className="w-3 h-3" />{WEATHER.temperature}°C</div>
        <div className="flex items-center gap-1"><Droplets className="w-3 h-3" />{WEATHER.rain} mm</div>
        <div className="flex items-center gap-1">💧 {WEATHER.humidity}%</div>
        <div className="flex items-center gap-1"><Wind className="w-3 h-3" />{WEATHER.wind} km/h</div>
      </div>
    </div>
  );
}
