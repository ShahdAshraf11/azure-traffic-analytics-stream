

import json
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import psycopg2
import joblib

from kafka import KafkaConsumer
from kafka.errors import KafkaError

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "data_generator"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "alerts"))

from config import DB_CONFIG, KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
from aggregations import WindowAggregator
from alert_manager import AlertManager
from data_quality import DataQualityChecker, DataQualityStats

from common.district_mapper import get_district
from common.feature_store import FeatureStore
from inference.forecast_inference import ForecastService

# AI summary is optional —-> guard the import in case Gemini SDK isn't installed yet
try:
    from inference.ai_summary import AISummaryService, build_snapshot
    AI_SUMMARY_AVAILABLE = True
except Exception as e:
    AI_SUMMARY_AVAILABLE = False
    AI_SUMMARY_IMPORT_ERROR = str(e)


#  LOGGING

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "consumer.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("consumer")

MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


#  ML MODEL MANAGER (Phase A v2 — district + feature_store)
class ModelManager:
    """
    Loads Phase A v2 models and provides:
      - compute_features() — builds RF/IF input from raw Kafka message
      - predict_congestion() — applies closure rule then runs RF
      - detect_anomaly() — runs Isolation Forest

    Phase A v2 changes from v1:
      - No more `label_encoder_location.joblib` (replaced with district encoding)
      - Uses common.feature_store.FeatureStore for 3-tier fallback
      - Adds: district_target_encoded, loc_avg_speed, loc_avg_congestion
      - Drops: location_encoded
    """

    # The exact list the model was trained with (matches feature_columns.json)
    RF_FEATURES = [
        "current_speed", "free_flow_speed", "congestion_ratio",
        "speed_drop_pct", "delay_seconds", "speed_deviation",
        "hour", "day_of_week", "is_weekend", "is_rush_hour",
        "time_period", "month",
        "temperature", "humidity", "wind_speed", "rain_mm", "is_raining",
        "frc_encoded", "district_target_encoded",
        "loc_avg_speed", "loc_avg_congestion",
        "is_slow_road", "confidence",
    ]

    IF_FEATURES = [
        "current_speed", "free_flow_speed", "congestion_ratio",
        "speed_drop_pct", "delay_seconds", "speed_deviation",
        "hour", "is_rush_hour", "rain_mm", "wind_speed",
        "loc_avg_speed", "loc_avg_congestion",
    ]

    def __init__(self, models_dir):
        self.models_dir = models_dir
        self.rf_model = None
        self.iso_model = None
        self.iso_scaler = None
        self.le_frc = None
        self.feature_store = None  # 3-tier fallback for location stats

        # District-level target encoding (avg congestion per district)
        # Computed from the feature_store on load
        self.district_target_encoding = {}
        self.district_target_encoding_global = 0.71  # safe default

        self.loaded = False
        self._load_models()

    def _load_models(self):
        try:
            self.rf_model = joblib.load(
                os.path.join(self.models_dir, "random_forest_congestion.joblib"))
            self.iso_model = joblib.load(
                os.path.join(self.models_dir, "isolation_forest.joblib"))
            self.iso_scaler = joblib.load(
                os.path.join(self.models_dir, "anomaly_scaler.joblib"))
            self.le_frc = joblib.load(
                os.path.join(self.models_dir, "label_encoder_frc.joblib"))

            # Initialize feature store (reads common/location_stats.json)
            stats_path = os.path.join(PROJECT_ROOT, "common", "location_stats.json")
            self.feature_store = FeatureStore(stats_path=stats_path)

            # Build district target encoding from feature store
            # (avg congestion ratio per district)
            if self.feature_store.loaded:
                for district_name, stats in self.feature_store.districts.items():
                    self.district_target_encoding[district_name] = stats["avg_congestion_ratio"]
                self.district_target_encoding_global = (
                    self.feature_store.city_wide["avg_congestion_ratio"])

            self.loaded = True
            logger.info(f"Models loaded from {self.models_dir}")
            logger.info(f"  RF expects {self.rf_model.n_features_in_} features "
                        f"(we will provide {len(self.RF_FEATURES)})")
            logger.info(f"  IF expects {self.iso_model.n_features_in_} features "
                        f"(we will provide {len(self.IF_FEATURES)})")
            logger.info(f"  Feature store: {self.feature_store.summary()}")
            logger.info(f"  District encoding for {len(self.district_target_encoding)} districts")
        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            logger.error("Make sure Phase A v2 .joblib files are in models/")
            self.loaded = False

    def compute_features(self, msg):
        """
        Takes raw Kafka message, returns enriched dict with all derived features.

        Adds Phase A v2 features:
          - district (resolved from lat/lon or msg)
          - district_target_encoded (avg congestion for district)
          - loc_avg_speed, loc_avg_congestion (per-location stats with fallback)
        """
        #  Parse timestamp 
        ts = msg.get("request_time", "")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)

        current_speed = float(msg.get("current_speed", 0) or 0)
        free_flow_speed = float(msg.get("free_flow_speed", 0) or 0)
        current_tt = msg.get("current_travel_time", 0) or 0
        free_flow_tt = msg.get("free_flow_travel_time", 0) or 0
        location = msg.get("location_name", "")
        lat = msg.get("requested_lat", 0)
        lon = msg.get("requested_lon", 0)

        #  Basic derived features 
        congestion_ratio = current_speed / free_flow_speed if free_flow_speed > 0 else 0
        speed_drop_pct = (1 - congestion_ratio) * 100
        delay_seconds = max(0, current_tt - free_flow_tt)

        #  Time features 
        hour = ts.hour
        day_of_week = ts.weekday()  # Monday=0, Sunday=6
        # FIXED: Egypt weekend is Friday(4) + Saturday(5), not >= 4
        is_weekend = 1 if day_of_week in (4, 5) else 0
        month = ts.month

        #  Weather features 
        temperature = float(msg.get("weather_temp", 25.0) or 25.0)
        humidity = int(msg.get("weather_humid", 40) or 40)
        wind_speed = float(msg.get("weather_wind", 3.0) or 3.0)
        rain_mm = float(msg.get("weather_rain", 0.0) or 0.0)
        weather_main = msg.get("weather_main", "Clear") or "Clear"
        is_raining = 1 if rain_mm > 0 else 0

        #  Engineered time features
        is_rush_hour = 1 if (7 <= hour <= 9 or 16 <= hour <= 19) else 0
        if 0 <= hour <= 5:
            time_period = 0
        elif 6 <= hour <= 9:
            time_period = 1
        elif 10 <= hour <= 14:
            time_period = 2
        elif 15 <= hour <= 19:
            time_period = 3
        else:
            time_period = 4

        #  Phase A v2: district + feature_store lookup
        # Resolve district from message or coordinates
        district = msg.get("district")
        if not district and lat and lon:
            try:
                district = get_district(lat, lon)
            except Exception:
                district = "Unknown"
        district = district or "Unknown"

        # Look up location stats (3-tier fallback handles unknown locations)
        loc_stats = self.feature_store.get_location_stats(location, lat, lon)
        loc_avg_speed = loc_stats["avg_speed"]
        loc_avg_congestion = loc_stats["avg_congestion_ratio"]

        # District target encoding (model feature)
        district_target_encoded = self.district_target_encoding.get(
            district, self.district_target_encoding_global)

        # speed_deviation now uses location's typical speed (not training average)
        speed_deviation = current_speed - loc_avg_speed
        is_slow_road = 1 if free_flow_speed < 25 else 0

        #  Encode FRC 
        frc = msg.get("frc", "")
        frc_encoded = -1
        if self.le_frc and frc in self.le_frc.classes_:
            frc_encoded = int(self.le_frc.transform([frc])[0])

        #  Closure flag 
        road_closure_int = 1 if msg.get("road_closure") else 0

        #  Return everything 
        return {
            **msg,
            "district": district,
            "congestion_ratio": round(congestion_ratio, 4),
            "speed_drop_pct": round(speed_drop_pct, 2),
            "delay_seconds": delay_seconds,
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "month": month,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "rain_mm": rain_mm,
            "is_raining": is_raining,
            "weather_main": weather_main,
            "is_rush_hour": is_rush_hour,
            "time_period": time_period,
            "speed_deviation": round(speed_deviation, 2),
            "is_slow_road": is_slow_road,
            "road_closure_int": road_closure_int,
            "frc_encoded": frc_encoded,
            "loc_avg_speed": round(loc_avg_speed, 2),
            "loc_avg_congestion": round(loc_avg_congestion, 4),
            "district_target_encoded": round(district_target_encoded, 4),
        }

    def predict_congestion(self, features):
        """
        Apply closure rule first (skip ML if road_closure), else run RF.
        Returns (predicted_class, actual_class) tuple.
        """
        #  CLOSURE RULE: closures are deterministic, not learned 
        if features.get("road_closure"):
            return "Closed", "Closed"

        if not self.loaded or self.rf_model is None:
            return None, None

        # Build feature row in the EXACT order RF was trained on
        rf_input = {col: features.get(col, 0) for col in self.RF_FEATURES}
        rf_df = pd.DataFrame([rf_input])[self.RF_FEATURES]
        predicted = str(self.rf_model.predict(rf_df)[0])

        # Compute actual level for comparison
        r = features["congestion_ratio"]
        if r >= 0.75:
            actual = "Free Flow"
        elif r >= 0.50:
            actual = "Moderate"
        elif r >= 0.25:
            actual = "Heavy"
        else:
            actual = "Severe"

        return predicted, actual

    def detect_anomaly(self, features):
        if not self.loaded or self.iso_model is None:
            return False, 0.0, ""

        # Build feature row in the EXACT order IF was trained on
        iso_input = {col: features.get(col, 0) for col in self.IF_FEATURES}
        iso_df = pd.DataFrame([iso_input])[self.IF_FEATURES]
        scaled = self.iso_scaler.transform(iso_df)
        score = float(self.iso_model.decision_function(scaled)[0])
        prediction = int(self.iso_model.predict(scaled)[0])
        is_says_anomaly = prediction == -1

        #  POST-FILTER: only treat as anomaly if a real signal exists 
        is_meaningful = (
            score < -0.05 or                          # IF is confident it's weird
            features.get("road_closure", False) or    # explicit closure
            features.get("speed_drop_pct", 0) > 30    # real congestion (>30% drop)
        )
        is_anomaly = is_says_anomaly and is_meaningful

         # Build human-readable reason
        reason = ""
        if is_anomaly:
            reasons = []
            if features.get("road_closure"):
                reasons.append("road closure detected")
            if features["speed_drop_pct"] > 70:
                reasons.append(f"speed {features['speed_drop_pct']:.0f}% below free-flow")
            elif features["speed_drop_pct"] > 30:
                reasons.append(f"speed {features['speed_drop_pct']:.0f}% below free-flow")
            if features["speed_deviation"] < -10:
                reasons.append(f"speed {abs(features['speed_deviation']):.1f}km/h below road average")
            if features["rain_mm"] > 5:
                reasons.append(f"heavy rain ({features['rain_mm']}mm)")
            if not reasons:
                reasons.append(f"strong anomaly signal (score={score:.4f})")
            reason = "; ".join(reasons)

        return is_anomaly, round(score, 4), reason



#  FORECAST MANAGER (Phase B Step 6 — wraps ForecastService)
class ForecastManager:
    """
    Thin wrapper around ForecastService that the consumer uses.
    Handles cold-start gracefully by checking is_warm() first.
    """

    def __init__(self, models_dir):
        self.service = None
        self.loaded = False
        try:
            stats_path = os.path.join(PROJECT_ROOT, "common", "location_stats.json")
            buffer_path = os.path.join(PROJECT_ROOT, "logs", "forecast_buffers.pkl")

            class _Mapper:
                @staticmethod
                def get_district(lat, lon):
                    return get_district(lat, lon)

            self.service = ForecastService(
                models_dir=models_dir,
                stats_path=stats_path,
                district_mapper=_Mapper(),
                buffer_persist_path=buffer_path,
            )
            self.loaded = True
            logger.info("ForecastService loaded")
        except Exception as e:
            logger.error(f"ForecastService failed to load: {e}")
            self.loaded = False

    def update_and_predict(self, features):
        """
        Update buffer and (if warm) get forecasts.
        Returns dict {horizon: {speed, class, confidence}} or {}.
        """
        if not self.loaded or self.service is None:
            return {}
        try:
            self.service.update_buffer(features)
            if not self.service.is_warm(features.get("location_name", "")):
                return {}
            return self.service.predict(features)
        except Exception as e:
            logger.error(f"Forecast prediction failed: {e}")
            return {}

    def save_buffers(self):
        if self.service:
            try:
                self.service.save_buffers()
            except Exception as e:
                logger.warning(f"Could not save forecast buffers: {e}")


#  AI SUMMARY MANAGER (Phase B Step 7 — runs every 5 min)
class AISummaryManager:
    """
    Wraps Gemini AISummaryService. Runs in a background thread that wakes
    every N minutes, builds a snapshot from latest features, calls Gemini,
    and writes the result to the database.
    """

    def __init__(self, db_writer, refresh_interval_seconds=300):
        self.db = db_writer
        self.refresh_interval = refresh_interval_seconds  # default 5 min
        self.service = None
        self.loaded = False

        # Thread-safe storage for latest features per location
        # Updated by main loop, read by background thread
        self.latest_records = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None

        if not AI_SUMMARY_AVAILABLE:
            logger.warning(f"AI summary module unavailable: {AI_SUMMARY_IMPORT_ERROR}")
            return

        try:
            self.service = AISummaryService()
            self.loaded = True
            logger.info("AISummaryService loaded")
        except RuntimeError as e:
            logger.warning(f"AISummaryService not initialized: {e}")
            logger.warning("Set GEMINI_API_KEY env var to enable AI summaries")
            self.loaded = False

    def update_record(self, features):
        """Called by main loop on every message."""
        if not self.loaded:
            return
        location = features.get("location_name")
        if location:
            with self.lock:
                self.latest_records[location] = {
                    "location_name": location,
                    "district": features.get("district"),
                    "current_speed": features.get("current_speed"),
                    "congestion_level": features.get("predicted_congestion"),
                    "congestion_ratio": features.get("congestion_ratio"),
                    "speed_drop_pct": features.get("speed_drop_pct"),
                    "weather_main": features.get("weather_main"),
                    "rain_mm": features.get("rain_mm"),
                    "temperature": features.get("temperature"),
                    "request_time": features.get("request_time"),
                    "trend_30min": None,  # could be filled from forecast model later
                    "is_anomaly": features.get("is_anomaly", 0),
                }

    def start(self):
        if not self.loaded:
            return
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"AI summary background thread started (every {self.refresh_interval}s)")

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=5)

    def _run_loop(self):
        # Wait a bit before first call so we have data to summarize
        first_wait = min(60, self.refresh_interval)
        if self.stop_event.wait(first_wait):
            return

        while not self.stop_event.is_set():
            try:
                self._generate_one_summary()
            except Exception as e:
                logger.error(f"AI summary generation failed: {e}")
            # Wait for next interval (or stop)
            if self.stop_event.wait(self.refresh_interval):
                break

    def _generate_one_summary(self):
        # Snapshot the latest records
        with self.lock:
            records = list(self.latest_records.values())
        if not records:
            logger.debug("No records yet — skipping AI summary")
            return

        snapshot = build_snapshot(records, n_hotspots=4, n_free_flowing=2)
        result = self.service.generate_summary(snapshot)

        if result.text and not result.error:
            logger.info(f"AI Summary: {result.text}")
        else:
            logger.warning(f"AI summary failed: {result.error}")

        # Save to database (even if it failed, store the error for debugging)
        self.db.save_ai_summary(snapshot, result)


#  DATABASE WRITER (extended for forecasts + ai_summaries)
class ConsumerDBWriter:
    """Handles all database writes for the consumer."""

    def __init__(self):
        self.connection = None
        self.lock = threading.Lock()  # so background AI thread can safely write
        self._connect()

    def _connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("Consumer connected to PostgreSQL")
        except psycopg2.OperationalError as e:
            logger.error(f"Could not connect to PostgreSQL: {e}")

    def _execute(self, sql, data):
        """Centralized execute with lock + error handling."""
        if not self.connection:
            return False
        with self.lock:
            try:
                cur = self.connection.cursor()
                cur.execute(sql, data)
                self.connection.commit()
                cur.close()
                return True
            except Exception as e:
                logger.error(f"DB write failed: {e}")
                try:
                    self.connection.rollback()
                except Exception:
                    pass
                return False

    def save_aggregation(self, agg):
        sql = """
            INSERT INTO traffic_aggregates (
                window_start, window_end, location_name,
                avg_speed, min_speed, max_speed,
                avg_free_flow_speed, avg_congestion_ratio,
                reading_count, closure_count
            ) VALUES (
                %(window_start)s, %(window_end)s, %(location_name)s,
                %(avg_speed)s, %(min_speed)s, %(max_speed)s,
                %(avg_free_flow_speed)s, %(avg_congestion_ratio)s,
                %(reading_count)s, %(closure_count)s
            )
        """
        return self._execute(sql, agg)

    def save_anomaly(self, features, score, reason):
        sql = """
            INSERT INTO anomalies (
                detected_at, location_name, anomaly_score,
                current_speed, free_flow_speed, congestion_ratio, reason
            ) VALUES (
                %(detected_at)s, %(location_name)s, %(anomaly_score)s,
                %(current_speed)s, %(free_flow_speed)s, %(congestion_ratio)s, %(reason)s
            )
        """
        data = {
            "detected_at": features.get("request_time", datetime.now(timezone.utc).isoformat()),
            "location_name": features.get("location_name", ""),
            "anomaly_score": float(score),
            "current_speed": float(features.get("current_speed", 0)),
            "free_flow_speed": float(features.get("free_flow_speed", 0)),
            "congestion_ratio": float(features.get("congestion_ratio", 0)),
            "reason": reason,
        }
        return self._execute(sql, data)

    def save_prediction(self, features, predicted, actual):
        sql = """
            INSERT INTO predictions (
                predicted_at, location_name, predicted_congestion,
                actual_congestion, confidence,
                top_reason_1, top_reason_2, top_reason_3
            ) VALUES (
                %(predicted_at)s, %(location_name)s, %(predicted_congestion)s,
                %(actual_congestion)s, %(confidence)s,
                %(top_reason_1)s, %(top_reason_2)s, %(top_reason_3)s
            )
        """
        # Build simple explanation reasons
        reasons = []
        if features.get("road_closure_int"):
            reasons.append("road_closure flag is active")
        if features.get("is_rush_hour"):
            reasons.append(f"rush hour (hour={features['hour']})")
        if features.get("speed_deviation", 0) < -5:
            reasons.append(f"speed {abs(features['speed_deviation']):.1f}km/h below average")
        if features.get("speed_deviation", 0) > 5:
            reasons.append(f"speed {features['speed_deviation']:.1f}km/h above average")
        if features.get("rain_mm", 0) > 0:
            reasons.append(f"rain: {features['rain_mm']}mm")
        while len(reasons) < 3:
            reasons.append("")

        data = {
            "predicted_at": features.get("request_time", datetime.now(timezone.utc).isoformat()),
            "location_name": features.get("location_name", ""),
            "predicted_congestion": str(predicted),
            "actual_congestion": str(actual),
            "confidence": float(features.get("confidence", 0)),
            "top_reason_1": reasons[0],
            "top_reason_2": reasons[1],
            "top_reason_3": reasons[2],
        }
        return self._execute(sql, data)

    def save_forecast(self, location_name, forecast_made_at, horizon, prediction):
        """
        Save a single forecast row.
          horizon: '20min', '30min', or '60min'
          prediction: dict from ForecastService with 'speed', 'class', 'confidence'
        """
        if prediction is None:
            return False
        sql = """
            INSERT INTO forecasts (
                forecast_made_at, location_name, horizon, target_time,
                predicted_speed, predicted_class, confidence
            ) VALUES (
                %(forecast_made_at)s, %(location_name)s, %(horizon)s, %(target_time)s,
                %(predicted_speed)s, %(predicted_class)s, %(confidence)s
            )
        """
        # Compute target_time from horizon
        try:
            made_at_dt = datetime.fromisoformat(str(forecast_made_at).replace("Z", "+00:00"))
        except Exception:
            made_at_dt = datetime.now(timezone.utc)
        offset_minutes = {"20min": 20, "30min": 30, "60min": 60}.get(horizon, 0)
        target_time = made_at_dt + timedelta(minutes=offset_minutes)

        data = {
            "forecast_made_at": made_at_dt.isoformat(),
            "location_name": location_name,
            "horizon": horizon,
            "target_time": target_time.isoformat(),
            "predicted_speed": float(prediction.get("speed", 0)),
            "predicted_class": str(prediction.get("class", "")),
            "confidence": float(prediction.get("confidence", 0)),
        }
        return self._execute(sql, data)

    def save_ai_summary(self, snapshot, result):
        sql = """
            INSERT INTO ai_summaries (
                generated_at, summary_text, snapshot_data,
                tokens_in, tokens_out, elapsed_ms, cached, error
            ) VALUES (
                %(generated_at)s, %(summary_text)s, %(snapshot_data)s,
                %(tokens_in)s, %(tokens_out)s, %(elapsed_ms)s, %(cached)s, %(error)s
            )
        """
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_text": result.text or "",
            "snapshot_data": json.dumps(snapshot, default=str),
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "elapsed_ms": result.elapsed_ms,
            "cached": result.cached,
            "error": result.error,
        }
        return self._execute(sql, data)

    def save_dq_event(self, location_name, result, raw_message):
        """Save one data quality check result to data_quality_events."""
        sql = """
            INSERT INTO data_quality_events (
                checked_at, location_name, quality_score, passed,
                issues_count, issues, raw_message
            ) VALUES (
                %(checked_at)s, %(location_name)s, %(quality_score)s, %(passed)s,
                %(issues_count)s, %(issues)s, %(raw_message)s
            )
        """
        data = {
            "checked_at":    datetime.now(timezone.utc).isoformat(),
            "location_name": location_name,
            "quality_score": result.score,
            "passed":        result.passed,
            "issues_count":  len(result.issues),
            "issues":        json.dumps(result.issues),
            "raw_message":   json.dumps(raw_message, default=str),
        }
        return self._execute(sql, data)

    def save_alert(self, alert):
        sql = """
            INSERT INTO alerts (
                triggered_at, location_name, alert_type, message, delivered
            ) VALUES (
                %(triggered_at)s, %(location_name)s, %(alert_type)s,
                %(message)s, %(delivered)s
            )
        """
        return self._execute(sql, alert)

    def is_connected(self):
        if not self.connection:
            return False
        try:
            cur = self.connection.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception:
            return False

    def reconnect(self):
        logger.warning("Consumer DB connection lost. Reconnecting...")
        try:
            if self.connection:
                self.connection.close()
        except Exception:
            pass
        self.connection = None
        self._connect()

    def close(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            logger.info("Consumer DB connection closed")


#  MAIN LOOP

def run():
    logger.info("=" * 60)
    logger.info("  Traffic Analytics Consumer (Phase C) — Starting")
    logger.info("=" * 60)

    # 1. ML models (Phase A v2)
    logger.info("Loading Phase A v2 ML models...")
    model_mgr = ModelManager(MODELS_DIR)
    if not model_mgr.loaded:
        logger.error("Phase A models not loaded — predictions will be skipped")

    # 2. Forecast service (Phase B)
    logger.info("Loading forecast service (Phase B)...")
    forecast_mgr = ForecastManager(MODELS_DIR)

    # 3. Database
    logger.info("Connecting to database...")
    db = ConsumerDBWriter()

    # 4. AI summary (Phase B Step 7)
    logger.info("Initializing AI summary service...")
    ai_summary = AISummaryManager(db, refresh_interval_seconds=300)
    ai_summary.start()  # starts background thread

    # 5. Aggregator + alerts (unchanged)
    logger.info("Initializing 5-minute window aggregator...")
    aggregator = WindowAggregator(window_size_minutes=5)

    logger.info("Initializing alert manager...")
    alert_mgr = AlertManager(db)

    #  DQ Pipeline 
    logger.info("Initializing data quality checker...")
    dq_checker = DataQualityChecker()
    dq_stats = DataQualityStats()

    # 6. Kafka
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    logger.info(f"Subscribing to topic: {KAFKA_TOPIC}")
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="traffic-consumer-group",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info("Kafka consumer connected — waiting for messages...\n")
    except KafkaError as e:
        logger.error(f"Could not connect to Kafka: {e}")
        return

    #  Counters 
    msg_count = 0
    anomaly_count = 0
    prediction_count = 0
    agg_count = 0
    forecast_count = 0
    round_buffer = []

    try:
        for kafka_msg in consumer:
            msg_count += 1
            msg = kafka_msg.value
            location = msg.get("location_name", "?")

            #  STEP 0: Data Quality Check (NEW) 
            # Validate the message before doing anything expensive.
            # Drop messages that fail. Log all results to DB.
            dq_result = dq_checker.check(msg)
            dq_stats.update(dq_result)
            db.save_dq_event(location, dq_result, msg)

            if not dq_result.passed:
                # Log and skip —> bad data shouldn't reach the ML pipeline
                logger.warning(
                    f"DQ FAIL: {location} | score={dq_result.score} | "
                    f"{len(dq_result.issues)} issues: "
                    f"{[i['message'] for i in dq_result.issues[:2]]}"
                )
                continue

            if dq_result.score < 80 and dq_result.issues:
                # Passed but with warnings —> log the warnings
                logger.info(
                    f"DQ WARN: {location} | score={dq_result.score} | "
                    f"{[i['message'] for i in dq_result.issues[:2]]}"
                )
            #  STEP 1: Compute features 
            try:
                features = model_mgr.compute_features(msg)
            except Exception as e:
                logger.error(f"Feature computation failed for {location}: {e}")
                continue

            #  STEP 2: Anomaly detection 
            is_anomaly, score, reason = model_mgr.detect_anomaly(features)
            if is_anomaly:
                anomaly_count += 1
                logger.warning(
                    f"ANOMALY #{anomaly_count}: {location} | "
                    f"speed={features['current_speed']}km/h | "
                    f"score={score} | {reason}"
                )
                db.save_anomaly(features, score, reason)

            #  STEP 3: Congestion prediction (with closure rule) 
            predicted, actual = model_mgr.predict_congestion(features)
            if predicted:
                prediction_count += 1
                match = "OK" if predicted == actual else "??"
                logger.info(
                    f"  [{match}] {location:25s} | "
                    f"speed={features['current_speed']:5.1f} | "
                    f"district={features['district']:15s} | "
                    f"predicted={predicted:10s} actual={actual:10s}"
                )
                db.save_prediction(features, predicted, actual)

            #  STEP 4: Forecasts (Phase B)
            forecasts = forecast_mgr.update_and_predict(features)
            if forecasts:
                forecast_made_at = features.get("request_time",
                                                 datetime.now(timezone.utc).isoformat())
                for horizon, pred in forecasts.items():
                    if pred:
                        db.save_forecast(location, forecast_made_at, horizon, pred)
                        forecast_count += 1

            #  STEP 5: Window aggregation 
            completed_windows = aggregator.add_message(features)
            for agg in completed_windows:
                agg_count += 1
                db.save_aggregation(agg)

            #  STEP 6: AI summary update (in-memory only here) 
            features["predicted_congestion"] = predicted
            features["is_anomaly"] = is_anomaly
            features["anomaly_score"] = score
            features["anomaly_reason"] = reason
            ai_summary.update_record(features)

            #  STEP 7: Alert evaluation 
            round_buffer.append(features)
            buffer_locations = [f.get("location_name") for f in round_buffer]
            if location in buffer_locations[:-1]:
                alert_mgr.evaluate(round_buffer[:-1])
                round_buffer = [features]

            #  Periodic status 
            if msg_count % 50 == 0:
                alert_stats = alert_mgr.get_stats()
                logger.info(
                    f"\n--- Status: {msg_count} msgs | "
                    f"{anomaly_count} anomalies | "
                    f"{prediction_count} predictions | "
                    f"{forecast_count} forecasts | "
                    f"{agg_count} windows | "
                    f"{alert_stats['total_alerts']} alerts ---\n"
                )
                logger.info(f"  {dq_stats.summary()}")
                if not db.is_connected():
                    db.reconnect()

    except KeyboardInterrupt:
        logger.info("\nStopped by user (Ctrl+C)")

    finally:
        if round_buffer:
            alert_mgr.evaluate(round_buffer)
        try:
            consumer.close()
        except Exception:
            pass
        ai_summary.stop()
        forecast_mgr.save_buffers()
        db.close()
        alert_stats = alert_mgr.get_stats()
        logger.info(
            f"\nConsumer shut down. {msg_count} msgs | "
            f"{anomaly_count} anomalies | {prediction_count} predictions | "
            f"{forecast_count} forecasts | {agg_count} windows | "
            f"{alert_stats['total_alerts']} alerts."
        )


if __name__ == "__main__":
    run()