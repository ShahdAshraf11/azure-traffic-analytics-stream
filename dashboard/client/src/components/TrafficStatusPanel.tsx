import { ROADS, getCongestionBg, getCongestionTailwind, type CongestionLevel } from "@/data/mockData";

export function TrafficStatusPanel() {
  const counts: Record<CongestionLevel, number> = {
    'Free Flow': 0, 'Moderate': 0, 'Heavy': 0, 'Severe': 0, 'Closed': 0,
  };
  ROADS.forEach((r) => counts[r.congestion]++);
  const total = ROADS.length;

  const topCritical = [...ROADS]
    .sort((a, b) => a.currentSpeed - b.currentSpeed)
    .slice(0, 5);

  return (
    <div className="space-y-3">
      {/* Donut overview */}
      <div className="bg-card rounded-lg border border-border p-3">
        <h3 className="text-xs font-semibold text-foreground mb-3">Traffic Status Overview</h3>
        <div className="flex items-center gap-4">
          <div className="relative w-20 h-20">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              {Object.entries(counts).reduce((acc, [level, count], i) => {
                const pct = (count / total) * 100;
                const offset = acc.offset;
                const colors: Record<string, string> = {
                  'Free Flow': 'hsl(142,71%,45%)',
                  'Moderate': 'hsl(48,96%,53%)',
                  'Heavy': 'hsl(25,95%,53%)',
                  'Severe': 'hsl(0,84%,60%)',
                  'Closed': 'hsl(220,9%,46%)',
                };
                acc.elements.push(
                  <circle
                    key={level}
                    cx="18" cy="18" r="15.5"
                    fill="none"
                    stroke={colors[level]}
                    strokeWidth="4"
                    strokeDasharray={`${pct} ${100 - pct}`}
                    strokeDashoffset={-offset}
                  />
                );
                acc.offset += pct;
                return acc;
              }, { elements: [] as React.ReactNode[], offset: 0 }).elements}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-bold text-foreground">{total}</span>
              <span className="text-[8px] text-muted-foreground">Total Roads</span>
            </div>
          </div>
          <div className="space-y-1 text-[10px]">
            {(Object.entries(counts) as [CongestionLevel, number][]).map(([level, count]) => (
              <div key={level} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${getCongestionBg(level)}`} />
                <span className="text-muted-foreground">{level}</span>
                <span className="text-foreground font-medium">
                  {count} ({((count / total) * 100).toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Critical */}
      <div className="bg-card rounded-lg border border-border p-3">
        <h3 className="text-xs font-semibold text-foreground mb-2">Top Critical Roads</h3>
        <div className="space-y-1.5">
          {topCritical.map((road, i) => (
            <div key={road.id} className="flex items-center gap-2 text-[10px]">
              <span className="text-muted-foreground w-3">{i + 1}</span>
              <span className="text-foreground flex-1 truncate">{road.name}</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${getCongestionBg(road.congestion)} text-foreground`}>
                {road.congestion}
              </span>
              <span className="text-muted-foreground w-12 text-right">{road.currentSpeed} km/h</span>
            </div>
          ))}
        </div>
        <button className="text-xs text-primary hover:underline mt-2">View All Roads →</button>
      </div>
    </div>
  );
}
