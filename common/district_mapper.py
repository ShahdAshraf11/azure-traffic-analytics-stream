"""
district_mapper.py
─────────────────────────────────────────────────────────────────
Maps any (latitude, longitude) coordinate in Cairo to a district name.

WHY THIS EXISTS:
   Our ML models need to handle NEW locations they've never seen during
   training. Instead of using "location_name" (which is unique per road),
   we use "district" — a higher-level grouping that GENERALIZES.

   A new road in "Downtown Cairo" will get the same district as Tahrir
   Square, so the model can use district-level patterns to make sensible
   predictions even on day one.

STRATEGY (two-tier):
   Tier 1: POLYGON CHECK
       - We define rough rectangular boundaries for each Cairo district.
       - If the point falls inside any polygon, we return that district.
       - Fast, deterministic, accurate for points clearly inside an area.

   Tier 2: NEAREST-NEIGHBOR FALLBACK
       - If no polygon contains the point, we find the closest known
         location and return ITS district.
       - This handles edge cases (boundaries, far-out roads, etc.)

PUBLIC API:
   get_district(lat, lon) -> str          # Main function
   get_all_districts() -> list[str]       # List of all known districts
"""

import math
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
#  DISTRICT POLYGON DEFINITIONS
#  Format: { district_name: (lat_min, lat_max, lon_min, lon_max) }
#  Order matters: more specific polygons first (Manial before Old Cairo).
# ═══════════════════════════════════════════════════════════════════

DISTRICT_POLYGONS = {
    # ─── Far south — Maadi ───
    "Maadi": (29.9200, 30.0050, 31.2400, 31.3000),

    # ─── West side of the Nile — Giza ───
    # Includes Pyramids/Haram corridor + extends east to ~31.220 to capture
    # Ahmed Oraby (lon=31.213) and Gamal Abd El-Nasser (lon=31.217).
    # North boundary 30.070 (stays south of Shobra).
    "Giza": (29.9500, 30.0700, 31.1000, 31.2200),

    # ─── Heliopolis (north-east) ───
    "Heliopolis": (30.0800, 30.1300, 31.2700, 31.3600),

    # ─── Shobra (north of downtown) ───
    "Shobra": (30.0700, 30.1050, 31.2200, 31.2700),

    # ─── Nasr City + Salah Salem corridor (east of downtown) ───
    # West boundary at 31.255 so it does NOT claim El-Gaish (lon=31.254),
    # which is now Downtown Cairo.
    "Nasr City": (30.0300, 30.0800, 31.2550, 31.3600),

    # ─── Manial (Rawda island + immediate west bank, on the Nile) ───
    # MUST be checked BEFORE Old Cairo — it's a thin strip nested inside.
    # Locations: El-Rawda, Al Manial, Al Malik Al Mozafar, Abdulaziz Al Saud
    # All sit between lon 31.222 and 31.228. Lat 30.012 → 30.024.
    "Manial": (30.0050, 30.0290, 31.2200, 31.2280),

    # ─── Old Cairo (east of Manial, south of Downtown) ───
    # Locations: Amro Ibn Al Aas (lon=31.229), Magra El-Eyoun (lon=31.241).
    # Sits east of Manial, west of Nasr City, south of Downtown.
    "Old Cairo": (30.0050, 30.0300, 31.2280, 31.2550),

    # ─── Downtown Cairo (central area) ───
    # East boundary 31.260 captures El-Gaish (lon=31.254).
    # West boundary 31.220 (anything west of that = Giza).
    "Downtown Cairo": (30.0300, 30.0700, 31.2200, 31.2600),
}


# ═══════════════════════════════════════════════════════════════════
#  KNOWN LOCATIONS (used for nearest-neighbor fallback)
#  Each entry: (name, lat, lon, district)
#  These are the GROUND TRUTH — provided by the project owner based on
#  local knowledge of Cairo.
# ═══════════════════════════════════════════════════════════════════

KNOWN_LOCATIONS = [
    # Downtown Cairo
    ("Tahrir Square",            30.0444,   31.2357,   "Downtown Cairo"),
    ("Talaat Harb St",           30.0506,   31.2404,   "Downtown Cairo"),
    ("Ramses St",                30.052613, 31.237925, "Downtown Cairo"),
    ("El-Gomhoreya St",          30.0499,   31.2466,   "Downtown Cairo"),
    ("Nile Corniche",            30.047107, 31.231616, "Downtown Cairo"),
    ("October Bridge",           30.0603,   31.2446,   "Downtown Cairo"),
    ("El-Gaish St",              30.052268, 31.254252, "Downtown Cairo"),

    # Giza (west of Nile + Pyramids road)
    ("El Haram St",              30.015433, 31.214553, "Giza"),
    ("26th of July Corridor",    30.063321, 31.167581, "Giza"),
    ("King Faisal St",           30.004008, 31.174183, "Giza"),
    ("Ring Road",                29.999456, 31.119034, "Giza"),
    ("Ahmed Oraby St",           30.062267, 31.212831, "Giza"),
    ("Gamal Abd El-Nasser Rd",   30.051973, 31.216775, "Giza"),

    # Manial (Rawda island + west bank strip)
    ("El-Rawda St",              30.015822, 31.223920, "Manial"),
    ("Al Manial St",             30.012794, 31.224867, "Manial"),
    ("Al Malik Al Mozafar St",   30.014387, 31.223665, "Manial"),
    ("Abdulaziz Al Saud St",     30.023352, 31.223223, "Manial"),

    # Old Cairo
    ("Amro Ibn Al Aas St",       30.013521, 31.229385, "Old Cairo"),
    ("Magra El-Eyoun St",        30.020851, 31.240715, "Old Cairo"),

    # Nasr City / Salah Salem
    ("Nasr City Ring Road",      30.0626,   31.3417,   "Nasr City"),
    ("Salah Salem Road",         30.0396,   31.2657,   "Nasr City"),

    # Maadi
    ("Maadi Corniche",           29.957459, 31.250348, "Maadi"),
    ("Autostorad St",            29.997227, 31.278652, "Maadi"),

    # Shobra
    ("Shobra St",                30.092088, 31.245208, "Shobra"),

    # Heliopolis
    ("El-Qobba Bridge",          30.100566, 31.305483, "Heliopolis"),
]


# ═══════════════════════════════════════════════════════════════════
#  CORE LOGIC
# ═══════════════════════════════════════════════════════════════════

def _haversine_distance(lat1: float, lon1: float,
                        lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two (lat, lon) points in kilometers.
    Used for nearest-neighbor matching since plain Euclidean distance
    on lat/lon is wrong (1 degree of lon != 1 degree of lat).
    """
    R = 6371.0  # Earth's radius in km
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _check_polygons(lat: float, lon: float) -> Optional[str]:
    """
    Tier 1: Check whether (lat, lon) falls inside any defined polygon.

    Returns the district name on hit, or None if no polygon contains
    the point. Iterates in dict-insertion order so more specific
    polygons (e.g., Manial inside Old Cairo's lat range) get checked first.
    """
    for district, (lat_min, lat_max, lon_min, lon_max) in DISTRICT_POLYGONS.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return district
    return None


def _nearest_neighbor(lat: float, lon: float) -> str:
    """
    Tier 2: Find the closest known location and return its district.

    Guarantees we always return a district name, even for points
    far outside our polygons (e.g., new neighborhoods, edge cases).
    """
    closest_district = "Downtown Cairo"   # safe default
    smallest_distance = float("inf")

    for _, k_lat, k_lon, district in KNOWN_LOCATIONS:
        d = _haversine_distance(lat, lon, k_lat, k_lon)
        if d < smallest_distance:
            smallest_distance = d
            closest_district = district

    return closest_district


def get_district(lat: float, lon: float) -> str:
    """
    PUBLIC API — Map any (lat, lon) coordinate to a Cairo district.

    Tries polygon match first (fast, accurate inside known areas),
    falls back to nearest-neighbor (catches edge cases).

    Args:
        lat: Latitude in decimal degrees (e.g., 30.0444)
        lon: Longitude in decimal degrees (e.g., 31.2357)

    Returns:
        District name (str), e.g., "Downtown Cairo", "Maadi", "Manial"
    """
    # Sanity check: input must be roughly in the Cairo metro area
    if not (29.5 <= lat <= 30.5 and 30.5 <= lon <= 32.0):
        return _nearest_neighbor(lat, lon)

    # Tier 1: polygon
    district = _check_polygons(lat, lon)
    if district is not None:
        return district

    # Tier 2: nearest neighbor
    return _nearest_neighbor(lat, lon)


def get_all_districts() -> list:
    """Returns the list of all known district names."""
    return list(DISTRICT_POLYGONS.keys())


# ═══════════════════════════════════════════════════════════════════
#  SELF-TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  DISTRICT MAPPER — SELF TEST")
    print("=" * 70)

    print("\n[1] Verifying all 25 known locations get the EXPECTED district:")
    correct = 0
    wrong = 0
    for name, lat, lon, expected in KNOWN_LOCATIONS:
        actual = get_district(lat, lon)
        ok = actual == expected
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {name:30s} → {actual:18s} (expected {expected})")
        if ok:
            correct += 1
        else:
            wrong += 1
    print(f"\n  Result: {correct}/{len(KNOWN_LOCATIONS)} correct, {wrong} wrong")

    print("\n[2] Testing brand-new fictional locations (not in training data):")
    test_points = [
        ("Made-up downtown road",     30.0500,   31.2400),
        ("Made-up Maadi side road",   29.9700,   31.2600),
        ("Made-up Giza road",         30.0200,   31.1800),
        ("Made-up Heliopolis road",   30.1100,   31.3200),
        ("Made-up Shobra side road",  30.0800,   31.2300),
        ("Made-up Nasr City road",    30.0500,   31.3000),
        ("Made-up Manial road",       30.0150,   31.2240),
        ("Made-up Old Cairo road",    30.0180,   31.2350),
        ("Edge case: New Cairo",      30.0300,   31.4500),
        ("Edge case: 6th October",    29.9500,   31.0000),
    ]
    for desc, lat, lon in test_points:
        district = get_district(lat, lon)
        print(f"  {desc:30s} ({lat:.4f}, {lon:.4f}) → {district}")

    print("\n[3] All known districts:")
    for d in get_all_districts():
        print(f"     - {d}")
    print()
