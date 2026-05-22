import { MODEL_RESULTS, WEATHER, SPEED_OVER_TIME, CONGESTION_DISTRIBUTION, PREDICTION_ACCURACY, getCongestionTailwind, type CongestionLevel } from "@/data/mockData";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  ResponsiveContainer, Tooltip, Legend,
} from "recharts";
import { CloudRain, Droplets, Wind, Gauge, Eye } from "lucide-react";
import { useState, useEffect } from "react";

export function BottomPanels() {
  // Force re-render every 30s to pick up updated mutable data
  const [, setTick] = useState(0);
  useEffect(() => {
    const i = setInterval(() => setTick(t => t + 1), 30000);
    return () => clearInterval(i);
  }, []);
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {/* AI Model Results */}
      <div className="bg-card rounded-lg border border-border p-3 flex flex-col overflow-hidden">
        <h3 className="text-xs font-semibold text-foreground mb-2">
          AI Model Results <span className="text-muted-foreground font-normal">(Latest)</span>
        </h3>
        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left pb-1.5 font-normal">Road</th>
                <th className="text-left pb-1.5 font-normal">Prediction</th>
                <th className="text-center pb-1.5 font-normal">Anomaly</th>
                <th className="text-right pb-1.5 font-normal">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {MODEL_RESULTS.map((r) => (
                <tr key={r.road} className="border-t border-border">
                  <td className="py-1.5 text-foreground truncate max-w-[80px]">{r.road}</td>
                  <td className={`py-1.5 font-medium ${getCongestionTailwind(r.prediction as CongestionLevel)}`}>
                    {r.prediction}
                  </td>
                  <td className="py-1.5 text-center">
                    <span className={`text-[9px] font-semibold ${
                      r.anomaly ? "text-traffic-severe" : "text-muted-foreground"
                    }`}>
                      {r.anomaly ? "YES" : "NO"}
                    </span>
                  </td>
                  <td className="py-1.5 text-right text-foreground">{r.confidence}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-center mt-2">
          <button className="text-xs text-primary hover:underline">View All Predictions →</button>
        </div>
      </div>

      {/* Weather Insights */}
      <div className="bg-card rounded-lg border border-border p-3 flex flex-col overflow-hidden">
        <h3 className="text-xs font-semibold text-foreground mb-3">Weather Insights</h3>
        <div className="flex items-center justify-between gap-3 mb-4">
          <CloudRain className="w-14 h-14 text-primary shrink-0" />
          <div className="text-right">
            <p className="text-3xl font-bold text-foreground leading-none">{WEATHER.temperature}°C</p>
            <p className="text-xs text-muted-foreground mt-1">{WEATHER.condition}</p>
          </div>
        </div>
        <div className="space-y-1.5 text-[11px] flex-1">
          <div className="flex items-center gap-2">
            <Droplets className="w-3 h-3 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Humidity</span>
            <span className="text-foreground font-medium ml-auto">{WEATHER.humidity}%</span>
          </div>
          <div className="flex items-center gap-2">
            <Wind className="w-3 h-3 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Wind</span>
            <span className="text-foreground font-medium ml-auto">{WEATHER.wind} km/h</span>
          </div>
          <div className="flex items-center gap-2">
            <Gauge className="w-3 h-3 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Pressure</span>
            <span className="text-foreground font-medium ml-auto">{WEATHER.pressure} hPa</span>
          </div>
          <div className="flex items-center gap-2">
            <Eye className="w-3 h-3 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Visibility</span>
            <span className="text-foreground font-medium ml-auto">{WEATHER.visibility} km</span>
          </div>
        </div>
        {(() => {
          let text = "";
          let colorClass = "text-traffic-free";
          
          if (WEATHER.rain > 0 && WEATHER.condition === "Thunderstorm") {
            text = `⛈️ Thunderstorm active (${WEATHER.rain}mm) → expect major delays`;
            colorClass = "text-traffic-severe";
          } else if (WEATHER.rain > 5) {
            text = `🌧️ Heavy rain (${WEATHER.rain}mm) → significant congestion increase`;
            colorClass = "text-traffic-heavy";
          } else if (WEATHER.rain > 0) {
            text = `🌧️ Light rain (${WEATHER.rain}mm) → expect slower traffic`;
            colorClass = "text-traffic-moderate";
          } else if (WEATHER.condition === "Clear") {
            text = "☀️ Clear skies → normal traffic conditions";
            colorClass = "text-traffic-free";
          } else if (WEATHER.condition === "Clouds") {
            text = "☁️ Cloudy skies → normal traffic conditions";
            colorClass = "text-traffic-free";
          } else if (WEATHER.condition === "Fog" || WEATHER.condition === "Mist") {
            text = "🌫️ Low visibility → drivers slowing down, expect mild delays";
            colorClass = "text-traffic-moderate";
          } else if (WEATHER.condition === "Haze") {
            text = "🌫️ Hazy conditions → reduced visibility, drive carefully";
            colorClass = "text-traffic-moderate";
          } else if (WEATHER.condition === "Dust" || WEATHER.condition === "Sand") {
            text = "🏜️ Dust/Sand storm → poor visibility, expect significant delays";
            colorClass = "text-traffic-heavy";
          } else if (WEATHER.condition === "Smoke") {
            text = "💨 Smoky conditions → reduced visibility, expect delays";
            colorClass = "text-traffic-heavy";
          } else if (WEATHER.condition === "Drizzle") {
            text = "🌦️ Light drizzle → roads may be slippery, mild delays";
            colorClass = "text-traffic-moderate";
          } else if (WEATHER.condition === "Snow") {
            text = "❄️ Snow detected → rare for Cairo, expect major disruption";
            colorClass = "text-traffic-severe";
          } else {
            text = `🌤️ ${WEATHER.condition} → monitoring traffic conditions`;
            colorClass = "text-muted-foreground";
          }

          return <p className={`text-[10px] ${colorClass} mt-3 text-center`}>{text}</p>;
        })()}
      </div>

      {/* Speed Over Time */}
      <div className="bg-card rounded-lg border border-border p-3 flex flex-col overflow-hidden">
        <h3 className="text-xs font-semibold text-foreground mb-2">
          Speed Over Time <span className="text-muted-foreground font-normal">(24 Hours)</span>
        </h3>
        <div className="flex-1 h-36 w-full overflow-hidden">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={SPEED_OVER_TIME} margin={{ top: 20, right: 5, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
              <XAxis dataKey="hour" tick={{ fontSize: 8, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} interval={3} />
              <YAxis tick={{ fontSize: 8, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} width={30} />
              <Tooltip
                contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8, fontSize: 10 }}
                labelStyle={{ color: "hsl(220,13%,91%)" }}
              />
              <Legend verticalAlign="top" align="center" iconSize={8} wrapperStyle={{ fontSize: 9, paddingBottom: 4, top: 0 }} />
              <Line type="monotone" dataKey="ringRoad" stroke="hsl(217,91%,60%)" strokeWidth={1.5} dot={false} name="Ring Road" />
              <Line type="monotone" dataKey="salahSalem" stroke="hsl(0,84%,60%)" strokeWidth={1.5} dot={false} name="Salah Salem" />
              <Line type="monotone" dataKey="october" stroke="hsl(48,96%,53%)" strokeWidth={1.5} dot={false} name="6th of Oct." />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="text-center mt-1">
          <button className="text-xs text-primary hover:underline">View Full Analytics →</button>
        </div>
      </div>

      {/* Congestion Distribution */}
      <div className="bg-card rounded-lg border border-border p-3 flex flex-col overflow-hidden">
        <h3 className="text-xs font-semibold text-foreground mb-2">
          Congestion Distribution <span className="text-muted-foreground font-normal">(Today)</span>
        </h3>
        <div className="flex-1 h-36 w-full overflow-hidden">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={CONGESTION_DISTRIBUTION} margin={{ top: 20, right: 5, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217,33%,22%)" />
              <XAxis dataKey="hour" tick={{ fontSize: 7, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} interval={3} />
              <YAxis tick={{ fontSize: 8, fill: "hsl(218,11%,65%)" }} tickLine={false} axisLine={false} width={30} />
              <Tooltip
                contentStyle={{ background: "hsl(222,47%,15%)", border: "1px solid hsl(217,33%,22%)", borderRadius: 8, fontSize: 10 }}
              />
              <Legend verticalAlign="top" align="center" iconSize={8} wrapperStyle={{ fontSize: 9, paddingBottom: 4, top: 0 }} />
              <Bar dataKey="free" stackId="a" fill="hsl(142,71%,45%)" name="Free" />
              <Bar dataKey="moderate" stackId="a" fill="hsl(48,96%,53%)" name="Moderate" />
              <Bar dataKey="heavy" stackId="a" fill="hsl(25,95%,53%)" name="Heavy" />
              <Bar dataKey="severe" stackId="a" fill="hsl(0,84%,60%)" name="Severe" />
              <Bar dataKey="closed" stackId="a" fill="hsl(220,9%,46%)" name="Closed" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
