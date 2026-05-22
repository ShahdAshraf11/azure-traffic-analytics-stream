import { Activity, Bell, CloudRain, User } from "lucide-react";
import { WEATHER, ANOMALIES } from "@/data/mockData";
import { useState, useEffect } from "react";
import { DataQualityBadge } from "@/components/DataQualityBadge";

export function TopBar() {
  const [time, setTime] = useState(new Date());
  // Force re-read of WEATHER every second along with clock
  const [, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date());
      setTick(t => t + 1); // triggers re-render to pick up new WEATHER values
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-12 bg-surface-0 border-b border-border flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-traffic-free animate-pulse-dot" />
          <span className="text-sm font-medium text-foreground">Live Operation Center</span>
        </div>
        <div className="flex items-center gap-1 text-muted-foreground">
          <Activity className="w-3.5 h-3.5" />
          <svg className="w-16 h-4" viewBox="0 0 64 16">
            <polyline
              points="0,8 8,4 16,10 24,6 32,12 40,3 48,9 56,5 64,8"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            />
          </svg>
        </div>
        <span className="text-xs text-muted-foreground">
          Last Updated: <span className="text-foreground font-medium">{time.toLocaleTimeString()}</span>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <DataQualityBadge />
        <div className="flex items-center gap-2 text-sm">
          <CloudRain className="w-4 h-4 text-primary" />
          <span className="font-medium text-foreground">
            {WEATHER.temperature ? `${WEATHER.temperature}°C` : "—"}
          </span>
          <span className="text-muted-foreground text-xs">{WEATHER.condition}</span>
        </div>
        <div className="relative">
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-destructive text-[8px] text-destructive-foreground flex items-center justify-center font-bold">
            {ANOMALIES.length || 0}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center">
            <User className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="hidden lg:block">
            <p className="text-xs font-medium text-foreground leading-tight">Operator</p>
            <p className="text-[10px] text-muted-foreground">Traffic Control Center</p>
          </div>
        </div>
      </div>
    </header>
  );
}
