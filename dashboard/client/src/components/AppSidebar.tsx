import {
  Map, AlertTriangle, Brain, BarChart3, Activity, FileText,
  LayoutDashboard, TrendingUp, Shield
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { TrafficStatusPanel } from "@/components/TrafficStatusPanel";

const navItems = [
  { title: "Live Traffic Map", url: "/", icon: Map },
  { title: "Anomaly Feed", url: "/anomalies", icon: AlertTriangle },
  { title: "Forecasts", url: "/forecasts", icon: TrendingUp },             // NEW
  { title: "AI Explanations", url: "/explanations", icon: Brain },
  { title: "Traffic Analytics", url: "/analytics", icon: BarChart3 },
  { title: "Data Quality", url: "/data-quality", icon: Shield },           // NEW
  { title: "System Health", url: "/health", icon: Activity },
  { title: "Reports", url: "/reports", icon: FileText },
  { title: "Power BI Reports", url: "/powerbi", icon: LayoutDashboard },
];

export function AppSidebar() {
  const location = useLocation();

  return (
    <aside className="w-56 min-h-screen bg-surface-0 border-r border-border flex flex-col shrink-0 overflow-y-auto">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
            <Map className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground leading-tight">Egypt Smart Traffic</h1>
            <p className="text-[10px] text-muted-foreground">AI Monitoring System</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.url;
          return (
            <NavLink
              key={item.url}
              to={item.url}
              end
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
              activeClassName=""
            >
              <item.icon className="w-4 h-4 shrink-0" />
              <span>{item.title}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-foreground">System Status</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-traffic-free/20 text-traffic-free font-medium">
            Operational
          </span>
        </div>
        <p className="text-[10px] text-muted-foreground">All systems running smoothly</p>
        <div className="flex items-center gap-1.5 mt-2">
          <Activity className="w-3 h-3 text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground">Auto refresh every 30s</span>
        </div>
      </div>

      {/* Traffic Status Overview + Top Critical Roads */}
      <div className="px-3 py-3 border-t border-border flex-1">
        <TrafficStatusPanel />
      </div>
    </aside>
  );
}
