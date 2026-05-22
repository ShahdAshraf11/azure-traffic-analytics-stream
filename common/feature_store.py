"""
feature_store.py
─────────────────────────────────────────────────────────────────
Provides location-level statistics (avg speed, avg congestion, etc.)
used as features by the ML models and as fallback values for the consumer.

THREE-TIER FALLBACK:
   1. Per-location average  (best: built from this road's history)
   2. Per-district average  (good: same neighborhood behaves similarly)
   3. City-wide average     (acceptable: at least roughly Cairo-realistic)

PUBLIC API:
   FeatureStore(stats_path)                       # loads JSON once
   store.get_location_stats(name, lat, lon)       # all stats with fallback
   store.get_avg_speed(name, lat, lon)            # convenience getter
   store.get_avg_congestion(name, lat, lon)       # convenience getter
   store.is_known_location(name)                  # True/False
   store.summary()                                # diagnostic info

USAGE:
   from common.feature_store import FeatureStore
   store = FeatureStore()
   stats = store.get_location_stats("Tahrir Square", 30.0444, 31.2357)
"""

import json
import logging
import os
import sys
from typing import Optional

# Make district_mapper importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from district_mapper import get_district


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  DEFAULTS
# ═══════════════════════════════════════════════════════════════════

DEFAULT_STATS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "location_stats.json"
)

# Last-resort defaults if the JSON is missing or corrupt
HARDCODED_FALLBACK = {
    "avg_speed":            24.0,
    "avg_free_flow_speed":  34.0,
    "avg_congestion_ratio": 0.71,
    "avg_delay_seconds":    160.0,
}


# ═══════════════════════════════════════════════════════════════════
#  FEATURE STORE
# ═══════════════════════════════════════════════════════════════════

class FeatureStore:
    """Wraps location_stats.json with cached lookups + 3-tier fallback."""

    def __init__(self, stats_path: Optional[str] = None):
        self.stats_path = stats_path or DEFAULT_STATS_PATH
        self.locations = {}
        self.districts = {}
        self.city_wide = dict(HARDCODED_FALLBACK)
        self.loaded = False
        self._load()

    def _load(self) -> None:
        """Reads JSON and populates internal dicts."""
        if not os.path.exists(self.stats_path):
            logger.warning(
                f"location_stats.json not found at {self.stats_path} — "
                "feature store will use hardcoded fallback values only."
            )
            return
        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.locations = data.get("locations", {}) or {}
            self.districts = data.get("districts", {}) or {}
            cw = data.get("city_wide") or {}
            self.city_wide = {**HARDCODED_FALLBACK, **cw}
            self.loaded = True
            logger.info(
                f"FeatureStore loaded: {len(self.locations)} locations, "
                f"{len(self.districts)} districts."
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load {self.stats_path}: {e}")

    def get_location_stats(self,
                           location_name: str,
                           lat: Optional[float] = None,
                           lon: Optional[float] = None) -> dict:
        """Returns stats with 3-tier fallback. Always returns a valid dict."""
        # Tier 1: Per-location
        if location_name and location_name in self.locations:
            entry = self.locations[location_name]
            return {
                "avg_speed":            entry["avg_speed"],
                "avg_free_flow_speed":  entry["avg_free_flow_speed"],
                "avg_congestion_ratio": entry["avg_congestion_ratio"],
                "avg_delay_seconds":    entry["avg_delay_seconds"],
                "district":             entry.get("district", "Unknown"),
                "source":               "location",
            }

        if lat is None or lon is None:
            return self._city_wide_response("Unknown")

        district = get_district(lat, lon)

        # Tier 2: Per-district
        if district in self.districts:
            entry = self.districts[district]
            return {
                "avg_speed":            entry["avg_speed"],
                "avg_free_flow_speed":  entry["avg_free_flow_speed"],
                "avg_congestion_ratio": entry["avg_congestion_ratio"],
                "avg_delay_seconds":    entry["avg_delay_seconds"],
                "district":             district,
                "source":               "district",
            }

        # Tier 3: City-wide
        return self._city_wide_response(district)

    def _city_wide_response(self, district: str) -> dict:
        return {
            "avg_speed":            self.city_wide["avg_speed"],
            "avg_free_flow_speed":  self.city_wide["avg_free_flow_speed"],
            "avg_congestion_ratio": self.city_wide["avg_congestion_ratio"],
            "avg_delay_seconds":    self.city_wide["avg_delay_seconds"],
            "district":             district,
            "source":               "city_wide",
        }

    def get_avg_speed(self, location_name: str,
                      lat: Optional[float] = None,
                      lon: Optional[float] = None) -> float:
        return self.get_location_stats(location_name, lat, lon)["avg_speed"]

    def get_avg_congestion(self, location_name: str,
                           lat: Optional[float] = None,
                           lon: Optional[float] = None) -> float:
        return self.get_location_stats(location_name, lat, lon)["avg_congestion_ratio"]

    def is_known_location(self, location_name: str) -> bool:
        return location_name in self.locations

    def summary(self) -> dict:
        return {
            "loaded":          self.loaded,
            "stats_path":      self.stats_path,
            "n_locations":     len(self.locations),
            "n_districts":     len(self.districts),
            "city_avg_speed":  self.city_wide["avg_speed"],
        }


# ═══════════════════════════════════════════════════════════════════
#  SELF-TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  FEATURE STORE — SELF TEST")
    print("=" * 70)

    store = FeatureStore()
    print("\n[Summary]")
    for k, v in store.summary().items():
        print(f"  {k:18s}  {v}")

    print("\n[Tier 1] Known location 'Tahrir Square':")
    s = store.get_location_stats("Tahrir Square", 30.0444, 31.2357)
    print(f"  source={s['source']:10s}  avg_speed={s['avg_speed']:.2f}  district={s['district']}")

    print("\n[Tier 2] Brand-new road in Maadi (no history):")
    s = store.get_location_stats("Future Road A", 29.97, 31.26)
    print(f"  source={s['source']:10s}  avg_speed={s['avg_speed']:.2f}  district={s['district']}")

    print("\n[Tier 3] Coordinates outside Cairo:")
    s = store.get_location_stats("Mystery Road", 0.0, 0.0)
    print(f"  source={s['source']:10s}  avg_speed={s['avg_speed']:.2f}  district={s['district']}")
    print()
