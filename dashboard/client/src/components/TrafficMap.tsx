import { MapContainer } from "react-leaflet/MapContainer";
import { TileLayer } from "react-leaflet/TileLayer";
import { CircleMarker } from "react-leaflet/CircleMarker";
import { Polyline } from "react-leaflet/Polyline";
import { Marker } from "react-leaflet/Marker";
import { Popup } from "react-leaflet/Popup";
import L from "leaflet";
import { ROADS, getCongestionColor, type RoadData } from "@/data/mockData";
import { useState, useEffect } from "react";
import "leaflet/dist/leaflet.css";

interface TrafficMapProps {
  onSelectRoad?: (road: RoadData) => void;
}

interface Incident {
  incident_id: string;
  incident_type: string;
  magnitude: string;
  description: string;
  road_from: string;
  road_to: string;
  delay_seconds: number;
  lat: number;
  lon: number;
  start_time: string;
  near_road: string;
}

const TOMTOM_KEY = import.meta.env.VITE_TOMTOM_KEY || "";
const API = "http://localhost:5000/api";

// ═══════════════════════════════════════════════════════════
//  Road segment polylines — approximate paths for each road
//  Each array = [[lat,lng], [lat,lng], ...] points along the road
//  ~300-500m segments centered on the monitoring point
// ═══════════════════════════════════════════════════════════
const ROAD_PATHS: Record<string, [number, number][]> = {
  "Tahrir Square": [
    [30.0450, 31.2340], [30.0444, 31.2350], [30.0440, 31.2357], [30.0436, 31.2368], [30.0440, 31.2378],
  ],
  "Nasr City Ring Road": [
    [30.0626, 31.3370], [30.0626, 31.3390], [30.0626, 31.3417], [30.0628, 31.3440], [30.0630, 31.3465],
  ],
  "October Bridge": [
    [30.0608, 31.2400], [30.0605, 31.2420], [30.0603, 31.2446], [30.0600, 31.2470], [30.0597, 31.2495],
  ],
  "El-Rawda St": [
    [30.0180, 31.2237], [30.0170, 31.2238], [30.0158, 31.2239], [30.0148, 31.2240], [30.0138, 31.2241],
  ],
  "Maadi Corniche": [
    [29.9600, 31.2500], [29.9590, 31.2502], [29.9575, 31.2503], [29.9560, 31.2505], [29.9545, 31.2507],
  ],
  "El-Gomhoreya St": [
    [30.0520, 31.2464], [30.0510, 31.2465], [30.0499, 31.2466], [30.0488, 31.2467], [30.0477, 31.2468],
  ],
  "El-Gaish St": [
    [30.0545, 31.2525], [30.0535, 31.2533], [30.0523, 31.2543], [30.0510, 31.2553], [30.0500, 31.2560],
  ],
  "Salah Salem Road": [
    [30.0400, 31.2610], [30.0398, 31.2630], [30.0396, 31.2657], [30.0394, 31.2680], [30.0392, 31.2705],
  ],
  "Ramses St": [
    [30.0555, 31.2378], [30.0542, 31.2379], [30.0526, 31.2379], [30.0510, 31.2380], [30.0498, 31.2381],
  ],
  "Talaat Harb St": [
    [30.0530, 31.2402], [30.0520, 31.2403], [30.0506, 31.2404], [30.0492, 31.2405], [30.0480, 31.2406],
  ],
  "El Haram St": [
    [30.0175, 31.2125], [30.0168, 31.2133], [30.0154, 31.2146], [30.0142, 31.2157], [30.0130, 31.2168],
  ],
  "Nile Corniche": [
    [30.0500, 31.2314], [30.0490, 31.2315], [30.0471, 31.2316], [30.0455, 31.2317], [30.0440, 31.2318],
  ],
  "26th of July Corridor": [
    [30.0635, 31.1630], [30.0634, 31.1650], [30.0633, 31.1676], [30.0632, 31.1700], [30.0631, 31.1725],
  ],
  "Gamal Abd El-Nasser Rd": [
    [30.0522, 31.2130], [30.0521, 31.2148], [30.0520, 31.2168], [30.0519, 31.2188], [30.0518, 31.2208],
  ],
  "Shobra St": [
    [30.0950, 31.2451], [30.0940, 31.2451], [30.0921, 31.2452], [30.0905, 31.2453], [30.0890, 31.2453],
  ],
  "Abdulaziz Al Saud St": [
    [30.0255, 31.2230], [30.0245, 31.2231], [30.0234, 31.2232], [30.0222, 31.2233], [30.0212, 31.2234],
  ],
  "Al Manial St": [
    [30.0150, 31.2247], [30.0140, 31.2248], [30.0128, 31.2249], [30.0116, 31.2250], [30.0105, 31.2250],
  ],
  "Al Malik Al Mozafar St": [
    [30.0165, 31.2235], [30.0155, 31.2236], [30.0144, 31.2237], [30.0133, 31.2237], [30.0122, 31.2238],
  ],
  "Amro Ibn Al Aas St": [
    [30.0137, 31.2265], [30.0136, 31.2278], [30.0135, 31.2294], [30.0134, 31.2308], [30.0133, 31.2322],
  ],
  "Magra El-Eyoun St": [
    [30.0210, 31.2370], [30.0209, 31.2388], [30.0209, 31.2407], [30.0208, 31.2425], [30.0207, 31.2445],
  ],
  "Autostorad St": [
    [29.9995, 31.2750], [29.9985, 31.2765], [29.9972, 31.2787], [29.9960, 31.2805], [29.9948, 31.2825],
  ],
  "El-Qobba Bridge": [
    [30.1008, 31.3020], [30.1007, 31.3035], [30.1006, 31.3055], [30.1005, 31.3075], [30.1004, 31.3090],
  ],
  "King Faisal St": [
    [30.0042, 31.1705], [30.0041, 31.1722], [30.0040, 31.1742], [30.0039, 31.1762], [30.0038, 31.1780],
  ],
  "Ring Road": [
    [29.9998, 31.1150], [29.9996, 31.1170], [29.9995, 31.1190], [29.9993, 31.1215], [29.9992, 31.1235],
  ],
  "Ahmed Oraby St": [
    [30.0625, 31.2095], [30.0624, 31.2110], [30.0623, 31.2128], [30.0622, 31.2148], [30.0621, 31.2165],
  ],
};

// ═══════════════════════════════════════════════════════════
//  Incident markers
// ═══════════════════════════════════════════════════════════
const INCIDENT_STYLE: Record<string, { color: string; border: string; label: string }> = {
  "Accident":             { color: "#ef4444", border: "#fca5a5", label: "Accident" },
  "Jam":                  { color: "#f59e0b", border: "#fcd34d", label: "Traffic Jam" },
  "Road Closed":          { color: "#a855f7", border: "#c4b5fd", label: "Road Closed" },
  "Road Works":           { color: "#f97316", border: "#fdba74", label: "Road Works" },
  "Dangerous Conditions": { color: "#ef4444", border: "#fca5a5", label: "Danger Zone" },
  "Lane Closed":          { color: "#f97316", border: "#fdba74", label: "Lane Closed" },
  "Flooding":             { color: "#3b82f6", border: "#93c5fd", label: "Flooding" },
  "Broken Down Vehicle":  { color: "#6b7280", border: "#9ca3af", label: "Breakdown" },
};

const MAGNITUDE_LABEL: Record<string, { text: string; color: string }> = {
  "Minor":    { text: "Minor Impact", color: "#34d399" },
  "Moderate": { text: "Moderate Impact", color: "#fbbf24" },
  "Major":    { text: "Major Impact", color: "#f87171" },
};

function createDiamondIcon(type: string) {
  const style = INCIDENT_STYLE[type] || { color: "#f59e0b", border: "#fcd34d" };
  return L.divIcon({
    className: "",
    html: `<div style="
      width: 10px; height: 10px;
      background: ${style.color};
      border: 1.5px solid ${style.border};
      transform: rotate(45deg);
      box-shadow: 0 0 6px ${style.color}80, 0 1px 3px rgba(0,0,0,0.3);
      cursor: pointer;
    "></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
    popupAnchor: [0, -8],
  });
}

function IncidentLayer() {
  const [incidents, setIncidents] = useState<Incident[]>([]);

  useEffect(() => {
    const fetchIncidents = () => {
      fetch(`${API}/incidents?hours=2`)
        .then(r => r.json())
        .then(data => { if (Array.isArray(data)) setIncidents(data); })
        .catch(() => {});
    };
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {incidents.map((inc) => {
        if (!inc.lat || !inc.lon) return null;
        const cfg = INCIDENT_STYLE[inc.incident_type] || { color: "#f59e0b", border: "#fcd34d", label: inc.incident_type };
        const mag = MAGNITUDE_LABEL[inc.magnitude];
        const icon = createDiamondIcon(inc.incident_type);
        const delayMin = inc.delay_seconds > 0 ? Math.round(inc.delay_seconds / 60) : 0;
        const sinceTime = inc.start_time ? new Date(inc.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;

        return (
          <Marker key={inc.incident_id} position={[inc.lat, inc.lon]} icon={icon}>
            <Popup>
              <div style={{
                fontFamily: "'Outfit', sans-serif", padding: "14px 16px",
                minWidth: 220, maxWidth: 280,
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "4px 10px", borderRadius: 8,
                    background: `${cfg.color}18`, border: `1px solid ${cfg.color}35`,
                  }}>
                    <div style={{ width: 7, height: 7, background: cfg.color, transform: "rotate(45deg)", flexShrink: 0 }} />
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, color: cfg.color }}>{cfg.label}</span>
                  </div>
                  {mag && <span style={{ fontSize: "0.6rem", fontWeight: 600, color: mag.color }}>{mag.text}</span>}
                </div>

                {inc.near_road && (
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: "0.55rem", color: "#3d4a66", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 2 }}>
                      Affected Monitored Road
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#f0f4fc" }}>{inc.near_road}</div>
                  </div>
                )}

                <div style={{
                  padding: "8px 10px", borderRadius: 8, marginBottom: 10,
                  background: "rgba(56,189,248,0.04)", border: "1px solid rgba(56,189,248,0.06)",
                }}>
                  <div style={{ fontSize: "0.55rem", color: "#3d4a66", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 3 }}>
                    What happened
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#c5cee0", lineHeight: 1.4 }}>{inc.description}</div>
                </div>

                {(delayMin > 0 || sinceTime) && (
                  <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                    {delayMin > 0 && (
                      <div style={{
                        flex: 1, textAlign: "center", padding: "6px 8px", borderRadius: 8,
                        background: "rgba(251,191,36,0.06)", border: "1px solid rgba(251,191,36,0.1)",
                      }}>
                        <div style={{ fontSize: "0.5rem", color: "#3d4a66", fontWeight: 600 }}>DELAY</div>
                        <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#fbbf24", fontFamily: "'JetBrains Mono', monospace" }}>{delayMin} min</div>
                      </div>
                    )}
                    {sinceTime && (
                      <div style={{
                        flex: 1, textAlign: "center", padding: "6px 8px", borderRadius: 8,
                        background: "rgba(56,189,248,0.04)", border: "1px solid rgba(56,189,248,0.06)",
                      }}>
                        <div style={{ fontSize: "0.5rem", color: "#3d4a66", fontWeight: 600 }}>SINCE</div>
                        <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#38bdf8", fontFamily: "'JetBrains Mono', monospace" }}>{sinceTime}</div>
                      </div>
                    )}
                  </div>
                )}

                {inc.road_from && (
                  <div style={{ fontSize: "0.58rem", color: "#3d4a66", borderTop: "1px solid rgba(56,189,248,0.06)", paddingTop: 6, marginTop: 4 }}>
                    Location: {inc.road_from}{inc.road_to ? ` → ${inc.road_to}` : ""}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}

// ═══════════════════════════════════════════════════════════
//  Main Map Component
// ═══════════════════════════════════════════════════════════
export function TrafficMap({ onSelectRoad }: TrafficMapProps) {
  return (
    <div className="w-full h-full rounded-lg overflow-hidden" style={{ position: "relative" }}>
      {/* Legend */}
      <div style={{
        position: "absolute", bottom: 12, left: 12, zIndex: 1000,
        padding: "6px 12px", borderRadius: 8,
        background: "rgba(10,15,30,.9)", backdropFilter: "blur(8px)",
        border: "1px solid rgba(56,189,248,.08)",
        display: "flex", gap: 12, alignItems: "center",
      }}>
        {[
          { label: "Free Flow", color: "hsl(142,71%,45%)" },
          { label: "Moderate", color: "hsl(48,96%,53%)" },
          { label: "Heavy", color: "hsl(25,95%,53%)" },
          { label: "Severe", color: "hsl(0,84%,60%)" },
          { label: "Closed", color: "hsl(220,9%,46%)" },
        ].map(l => (
          <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 3 }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: l.color }} />
            <span style={{ fontSize: "0.55rem", color: "#6b7a99" }}>{l.label}</span>
          </div>
        ))}
        <div style={{ width: 1, height: 12, background: "rgba(56,189,248,.12)" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 3 }}>
          <div style={{ width: 6, height: 6, background: "#f59e0b", transform: "rotate(45deg)" }} />
          <span style={{ fontSize: "0.55rem", color: "#6b7a99" }}>Incident</span>
        </div>
      </div>

      <MapContainer center={[30.05, 31.24]} zoom={12} className="w-full h-full" zoomControl={true}>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        {/* Colored road segments — drawn from OUR predictions */}
        {ROADS.map((road) => {
          const path = ROAD_PATHS[road.name];
          if (!path) return null;
          const color = getCongestionColor(road.congestion);
          return (
            <Polyline
              key={`line-${road.id}`}
              positions={path}
              pathOptions={{
                color: color,
                weight: 5,
                opacity: 0.7,
                lineCap: "round",
                lineJoin: "round",
              }}
            />
          );
        })}

        {/* Road marker circles */}
        {ROADS.map((road) => (
          <CircleMarker
            key={road.id}
            center={[road.lat, road.lng]}
            radius={8}
            pathOptions={{
              color: getCongestionColor(road.congestion),
              fillColor: getCongestionColor(road.congestion),
              fillOpacity: 0.9,
              weight: 2,
            }}
            eventHandlers={{ click: () => onSelectRoad?.(road) }}
          />
        ))}

        {/* Incident diamonds */}
        <IncidentLayer />
      </MapContainer>
    </div>
  );
}