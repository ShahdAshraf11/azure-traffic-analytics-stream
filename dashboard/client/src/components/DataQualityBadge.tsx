import { ShieldCheck, ShieldAlert } from "lucide-react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

const API = "http://localhost:5000/api";

interface DQStats {
  pass_rate: number;
  total_messages: number;
  warnings: number;
  failed: number;
}

/**
 * Data Quality Trust Badge (used in TopBar)
 * ─────────────────────────────────────────
 * A small badge that shows the system's data trust level.
 * Click to navigate to the full Data Quality page.
 *
 * Reads from: GET /api/data-quality/stats?hours=1
 */
export function DataQualityBadge() {
  const [stats, setStats] = useState<DQStats | null>(null);

  useEffect(() => {
    const fetchStats = () => {
      fetch(`${API}/data-quality/stats?hours=1`)
        .then((r) => r.json())
        .then((data) => setStats(data))
        .catch(() => {});
    };
    fetchStats();
    const interval = setInterval(fetchStats, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (!stats || stats.total_messages === 0) {
    return null;
  }

  const passRate = stats.pass_rate;
  let icon = <ShieldCheck className="w-3.5 h-3.5" />;
  let textColor = "text-traffic-free";
  let bgColor = "bg-traffic-free/10";

  if (passRate < 90) {
    icon = <ShieldAlert className="w-3.5 h-3.5" />;
    textColor = "text-traffic-severe";
    bgColor = "bg-traffic-severe/10";
  } else if (passRate < 99) {
    icon = <ShieldAlert className="w-3.5 h-3.5" />;
    textColor = "text-traffic-moderate";
    bgColor = "bg-traffic-moderate/10";
  }

  return (
    <Link
      to="/data-quality"
      className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${bgColor} ${textColor} hover:opacity-80 transition-opacity`}
      title={`Data quality: ${stats.total_messages} checks last hour, ${stats.warnings} warnings, ${stats.failed} failures`}
    >
      {icon}
      <span className="text-xs font-medium">{passRate.toFixed(1)}%</span>
    </Link>
  );
}
