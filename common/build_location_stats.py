"""
build_location_stats.py
─────────────────────────────────────────────────────────────────
ONE-TIME SCRIPT — Run whenever the training data changes.

Reads training_data_v4.csv, computes statistical averages at three levels:
   1. Per location  (e.g., "Tahrir Square")
   2. Per district  (e.g., "Downtown Cairo")
   3. City-wide     (overall fallback)

Saves to common/location_stats.json which is loaded at runtime by
feature_store.py (and now also forecast_inference.py).

WHEN TO RE-RUN:
   - After collecting more real traffic data
   - After adding new locations
   - After regenerating training_data_v4.csv

USAGE (from project root):
   python common/build_location_stats.py
"""

import json
import os
import sys
import pandas as pd

# Make `common.district_mapper` importable when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from district_mapper import get_district


# ═══════════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════════

DEFAULT_DATA_PATH = os.environ.get(
    "TRAINING_DATA_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "training_data_v4.csv"
    ),
)

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "location_stats.json"
)


# ═══════════════════════════════════════════════════════════════════
#  STAT COMPUTATION
# ═══════════════════════════════════════════════════════════════════

def compute_stats(df: pd.DataFrame) -> dict:
    """Computes hierarchical stats: locations, districts, city-wide."""
    # Tag every row with its district
    print("  Tagging every row with its district…")
    if "district" not in df.columns:
        df["district"] = df.apply(
            lambda r: get_district(r["requested_lat"], r["requested_lon"]),
            axis=1
        )

    # ── City-wide stats ──
    print("  Computing city-wide averages…")
    city_wide = {
        "avg_speed":            float(df["current_speed"].mean()),
        "avg_free_flow_speed":  float(df["free_flow_speed"].mean()),
        "avg_congestion_ratio": float(df["congestion_ratio"].mean()),
        "avg_delay_seconds":    float(df["delay_seconds"].mean()),
        "sample_count":         int(len(df)),
    }

    # ── District-level stats ──
    print("  Computing district averages…")
    districts = {}
    for district_name, group in df.groupby("district"):
        districts[district_name] = {
            "avg_speed":            float(group["current_speed"].mean()),
            "avg_free_flow_speed":  float(group["free_flow_speed"].mean()),
            "avg_congestion_ratio": float(group["congestion_ratio"].mean()),
            "avg_delay_seconds":    float(group["delay_seconds"].mean()),
            "sample_count":         int(len(group)),
        }

    # ── Location-level stats ──
    print("  Computing per-location averages…")
    locations = {}
    for loc_name, group in df.groupby("location_name"):
        first = group.iloc[0]
        locations[loc_name] = {
            "avg_speed":            float(group["current_speed"].mean()),
            "avg_free_flow_speed":  float(group["free_flow_speed"].mean()),
            "avg_congestion_ratio": float(group["congestion_ratio"].mean()),
            "avg_delay_seconds":    float(group["delay_seconds"].mean()),
            "district":             str(first["district"]),
            "lat":                  float(first["requested_lat"]),
            "lon":                  float(first["requested_lon"]),
            "frc":                  str(first["frc"]),
            "sample_count":         int(len(group)),
        }

    return {
        "city_wide": city_wide,
        "districts": districts,
        "locations": locations,
    }


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main(data_path: str = DEFAULT_DATA_PATH,
         output_path: str = OUTPUT_PATH) -> None:
    print("=" * 70)
    print("  BUILD LOCATION STATS")
    print("=" * 70)
    print(f"  Input:  {data_path}")
    print(f"  Output: {output_path}\n")

    if not os.path.exists(data_path):
        print(f"  ERROR: training data file not found at {data_path}")
        print("         Set TRAINING_DATA_PATH env var or place the CSV at that path.")
        sys.exit(1)

    print("  Loading training CSV…")
    df = pd.read_csv(data_path)
    print(f"  Loaded {len(df):,} rows, {df['location_name'].nunique()} unique locations.\n")

    stats = compute_stats(df)

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, sort_keys=True, ensure_ascii=False)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"  City-wide avg speed:    {stats['city_wide']['avg_speed']:.2f} km/h")
    print(f"  Districts: {len(stats['districts'])}")
    for d, s in sorted(stats["districts"].items()):
        print(f"    {d:18s}  avg_speed={s['avg_speed']:6.2f}  samples={s['sample_count']:,}")
    print(f"  Locations: {len(stats['locations'])}")
    print(f"\n  ✅ Saved to: {output_path}")


if __name__ == "__main__":
    main()
