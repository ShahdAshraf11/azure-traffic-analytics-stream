
from __future__ import annotations

import json
import logging
import os
import pickle
from collections import deque
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


INTERVAL_MINUTES = 10

# How many rows to look back for each lag (must match training)
LAG_OFFSETS = {
    "10min": 1,
    "30min": 3,
    "1hr":   6,
    "1day":  144,    # 24 hours * 60 min / 10 min
}

# Buffer size: enough rows to compute the longest lag plus 1
BUFFER_SIZE = max(LAG_OFFSETS.values()) + 1

# Minimum history required to predict (without it, lag_1day is NaN)
MIN_HISTORY_FOR_FULL_PREDICTION = max(LAG_OFFSETS.values())


# Forecast horizons (must match training)
HORIZONS = ["20min", "30min", "60min"]


#  ROLLING BUFFER

class LocationBuffer:
    """Holds the last N readings for one location.

    Each entry is a small dict with the few fields lag features need:
      timestamp, current_speed, congestion_ratio, road_closure
    Anything else is recomputed at predict time from the latest record.
    """

    def __init__(self, maxlen: int = BUFFER_SIZE):
        self._buf: deque = deque(maxlen=maxlen)

    def append(self, record: dict) -> None:
        self._buf.append({
            "timestamp":         pd.to_datetime(record.get("request_time")),
            "current_speed":     float(record.get("current_speed", 0.0)),
            "congestion_ratio":  float(record.get("congestion_ratio", 0.0)),
            "road_closure":      bool(record.get("road_closure", False)),
        })

    def __len__(self) -> int:
        return len(self._buf)

    def get_lag(self, n_back: int, field: str) -> Optional[float]:
        """Returns value n_back rows ago. None if buffer doesn't go that far."""
        if len(self._buf) <= n_back:
            return None
        # The most recent entry is at index -1, lag 1 is at -2, lag N is at -(N+1)
        idx = -(n_back + 1)
        try:
            return float(self._buf[idx][field])
        except (IndexError, KeyError, ValueError):
            return None


#  FORECAST SERVICE

class ForecastService:
    """Loads the 6 forecast models + encoders and produces predictions
    from a single live record by maintaining per-location lag buffers."""

    def __init__(
        self,
        models_dir: str = "models",
        stats_path: Optional[str] = None,
        district_mapper=None,
        buffer_persist_path: Optional[str] = None,
    ):
        self.models_dir = models_dir
        self.stats_path = stats_path
        self.buffer_persist_path = buffer_persist_path

        # Per-location rolling buffers (created lazily on first record)
        self._buffers: dict[str, LocationBuffer] = {}

        # Cached encoder lookups so unknown values get a sensible default
        self._frc_known: set = set()
        self._district_known: set = set()

        #  Load models, encoders, metadata 
        self._load_artifacts()

        #  (Optional) load location stats for unknown-location fallback 
        self.location_stats = None
        if stats_path and os.path.exists(stats_path):
            with open(stats_path) as f:
                self.location_stats = json.load(f)
            logger.info(
                f"ForecastService loaded location_stats with "
                f"{len(self.location_stats.get('locations', {}))} locations and "
                f"{len(self.location_stats.get('districts', {}))} districts."
            )

        #  (Optional) district_mapper for inferring district from lat/lon 
        self.district_mapper = district_mapper

        #  (Optional) restore buffers from disk so consumer restart isn't cold 
        if buffer_persist_path and os.path.exists(buffer_persist_path):
            self._load_buffers(buffer_persist_path)

    #  Loading 
    def _load_artifacts(self) -> None:
        """Loads the 6 forecast models, 3 encoders, and metadata JSON."""
        d = self.models_dir

        # Speed regressors
        self.speed_models = {
            h: joblib.load(os.path.join(d, f"forecast_speed_{h}.joblib"))
            for h in HORIZONS
        }

        # Class classifiers
        self.class_models = {
            h: joblib.load(os.path.join(d, f"forecast_class_{h}.joblib"))
            for h in HORIZONS
        }

        # Encoders
        self.le_frc = joblib.load(os.path.join(d, "forecast_le_frc.joblib"))
        self.le_district = joblib.load(os.path.join(d, "forecast_le_district.joblib"))
        self.le_class = joblib.load(os.path.join(d, "forecast_le_class.joblib"))
        self._frc_known = set(self.le_frc.classes_)
        self._district_known = set(self.le_district.classes_)

        # Feature column order (must match training!)
        with open(os.path.join(d, "forecast_feature_columns.json")) as f:
            meta = json.load(f)
        self.features: list[str] = meta["features"]

        logger.info(
            f"ForecastService loaded {len(self.speed_models)} speed models + "
            f"{len(self.class_models)} class models, {len(self.features)} features."
        )

    #  Buffer management 
    def update_buffer(self, record: dict) -> None:
        """Append the latest reading to the per-location buffer.
        Call this on every TomTom message (whether or not we're predicting)."""
        loc = record.get("location_name")
        if not loc:
            return
        buf = self._buffers.setdefault(loc, LocationBuffer())
        buf.append(record)

    def buffer_size(self, location_name: str) -> int:
        return len(self._buffers.get(location_name, LocationBuffer()))

    def is_warm(self, location_name: str) -> bool:
        """True if this location has enough history for a full prediction."""
        return self.buffer_size(location_name) >= MIN_HISTORY_FOR_FULL_PREDICTION

    #  Feature engineering 
    def _safe_encode_frc(self, frc_value: Any) -> int:
        """Encodes FRC; falls back to 0 (FRC0 = highway) if unknown."""
        s = str(frc_value)
        if s in self._frc_known:
            return int(self.le_frc.transform([s])[0])
        logger.debug(f"Unknown FRC '{s}', defaulting to 0")
        return 0

    def _safe_encode_district(self, district_name: Any) -> int:
        """Encodes district; falls back to 0 if unknown."""
        s = str(district_name)
        if s in self._district_known:
            return int(self.le_district.transform([s])[0])
        logger.debug(f"Unknown district '{s}', defaulting to 0")
        return 0

    def _resolve_district(self, record: dict) -> str:
        """Get district from record, or compute from lat/lon if missing."""
        if record.get("district"):
            return str(record["district"])
        if self.district_mapper and record.get("requested_lat") and record.get("requested_lon"):
            try:
                return self.district_mapper.get_district(
                    record["requested_lat"], record["requested_lon"]
                )
            except Exception:
                pass
        return "Unknown"

    def _build_feature_row(self, record: dict) -> Optional[pd.DataFrame]:
        """Build the 32-feature row the models expect.

        Returns None if not enough history is available for ALL the lags.
        """
        loc = record.get("location_name")
        if not loc:
            return None
        buf = self._buffers.get(loc)
        if buf is None or len(buf) < MIN_HISTORY_FOR_FULL_PREDICTION:
            # Not enough history — can't compute lag_1day. Skip prediction.
            return None

        #  Pull lag values from buffer 
        # Note: buffer's last entry IS the current record (we appended in
        # update_buffer). So lag of N rows means buffer index -(N+1).
        lags = {}
        ok = True
        for label, n_back in LAG_OFFSETS.items():
            speed_lag = buf.get_lag(n_back, "current_speed")
            ratio_lag = buf.get_lag(n_back, "congestion_ratio")
            if speed_lag is None or ratio_lag is None:
                ok = False
                break
            lags[f"speed_lag_{label}"] = speed_lag
            lags[f"ratio_lag_{label}"] = ratio_lag
        if not ok:
            return None

        #  Trends 
        cur_speed = float(record.get("current_speed", 0.0))
        cur_ratio = float(record.get("congestion_ratio", 0.0))
        speed_trend_30min = cur_speed - lags["speed_lag_30min"]
        ratio_trend_30min = cur_ratio - lags["ratio_lag_30min"]

        #  Buildup features 
        # congestion_buildup_1hr: positive value means traffic getting worse over the last hour
        congestion_buildup_1hr = lags["ratio_lag_1hr"] - lags["ratio_lag_10min"]
        # buildup_acceleration: is the buildup itself accelerating?
        buildup_acceleration = (
            ratio_trend_30min - (lags["ratio_lag_1hr"] - lags["ratio_lag_30min"])
        )

        #  Time features 
        ts = pd.to_datetime(record.get("request_time"))
        hour = int(ts.hour)
        day_of_week = int(ts.dayofweek)
        is_weekend = int(day_of_week in (4, 5))   # Egyptian week: Fri/Sat
        is_rush_hour = int(
            (is_weekend == 0) and (hour in (7, 8, 9, 15, 16, 17, 18, 19))
        )
        month = int(ts.month)

        #  Categorical encodings 
        district = self._resolve_district(record)
        frc_encoded = self._safe_encode_frc(record.get("frc"))
        district_encoded = self._safe_encode_district(district)

        #  Assemble the row 
        row = {
            # Current state
            "current_speed":          cur_speed,
            "free_flow_speed":        float(record.get("free_flow_speed", 0.0)),
            "congestion_ratio":       cur_ratio,
            "speed_drop_pct":         float(record.get("speed_drop_pct", 0.0)),
            "delay_seconds":          float(record.get("delay_seconds", 0.0)),
            # Lag features
            **lags,
            # Trend
            "speed_trend_30min":      speed_trend_30min,
            "ratio_trend_30min":      ratio_trend_30min,
            # Buildup
            "congestion_buildup_1hr": congestion_buildup_1hr,
            "buildup_acceleration":   buildup_acceleration,
            # Time
            "hour":                   hour,
            "day_of_week":            day_of_week,
            "is_weekend":             is_weekend,
            "is_rush_hour":           is_rush_hour,
            "month":                  month,
            # Weather
            "temperature":            float(record.get("temperature", 24.0)),
            "humidity":               float(record.get("humidity", 55)),
            "wind_speed":             float(record.get("wind_speed", 2.0)),
            "rain_mm":                float(record.get("rain_mm", 0.0)),
            "is_raining":             int(record.get("is_raining", 0)),
            # Location/road
            "frc_encoded":            frc_encoded,
            "district_encoded":       district_encoded,
            "requested_lat":          float(record.get("requested_lat", 0.0)),
            "requested_lon":          float(record.get("requested_lon", 0.0)),
            # Quality
            "confidence":             float(record.get("confidence", 1.0)),
        }

        # Order columns exactly as the model expects
        return pd.DataFrame([[row[c] for c in self.features]], columns=self.features)

    #  Predict 
    def predict(self, record: dict) -> dict:
        """Run all 6 models on a single record. Returns a dict with up to
        3 entries (keyed by horizon: "20min", "30min", "60min"); empty dict
        if insufficient history.

        IMPORTANT: call update_buffer(record) BEFORE this so the current
        reading is included in the buffer. (The current reading itself
        is also one of the inputs.)
        """
        X = self._build_feature_row(record)
        if X is None:
            return {}   # cold-start; no forecast yet

        forecasts = {}
        for h in HORIZONS:
            try:
                # Speed
                pred_speed = float(self.speed_models[h].predict(X)[0])

                # Class
                class_idx = int(self.class_models[h].predict(X)[0])
                class_name = str(self.le_class.inverse_transform([class_idx])[0])

                # Confidence = max class probability
                proba = self.class_models[h].predict_proba(X)[0]
                confidence = float(np.max(proba))

                forecasts[h] = {
                    "speed":      round(pred_speed, 1),
                    "class":      class_name,
                    "confidence": round(confidence, 3),
                }
            except Exception as e:
                logger.error(f"Forecast {h} failed: {e}")
                forecasts[h] = None
        return forecasts

    #  Persistence (optional) 
    def save_buffers(self, path: Optional[str] = None) -> None:
        """Pickle the current per-location buffers so the consumer can warm-start
        next time it runs. Call from a SIGTERM handler / cleanup hook."""
        path = path or self.buffer_persist_path
        if not path:
            return
        snapshot = {
            loc: list(buf._buf)
            for loc, buf in self._buffers.items()
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(snapshot, f)
        logger.info(f"Saved {len(snapshot)} location buffers to {path}")

    def _load_buffers(self, path: str) -> None:
        try:
            with open(path, "rb") as f:
                snapshot = pickle.load(f)
            for loc, items in snapshot.items():
                buf = LocationBuffer()
                buf._buf.extend(items)
                self._buffers[loc] = buf
            logger.info(f"Restored {len(self._buffers)} buffers from {path}")
        except Exception as e:
            logger.warning(f"Failed to restore buffers from {path}: {e}")

