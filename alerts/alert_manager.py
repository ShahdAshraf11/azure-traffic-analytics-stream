
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("alerts")

# Cooldown: don't repeat the same alert type + location within this many minutes
ALERT_COOLDOWN_MINUTES = 10


class AlertManager:
    """
    Evaluates traffic data for alert conditions and writes to the database.
    Tracks recent alerts in memory to avoid duplicates.
    """

    def __init__(self, db_writer):
        self.db = db_writer
        # In-memory cache: {(alert_type, location_name): last_alert_time}
        self.recent_alerts = {}
        # Track previous closure state to detect NEW closures
        self.previous_closures = set()
        self.alert_count = 0

    def _is_on_cooldown(self, alert_type, location_name):
        """Check if we already sent this alert recently."""
        key = (alert_type, location_name)
        if key in self.recent_alerts:
            elapsed = datetime.now(timezone.utc) - self.recent_alerts[key]
            if elapsed < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                return True
        return False

    def _record_alert(self, alert_type, location_name):
        """Mark this alert as sent so we don't repeat it."""
        self.recent_alerts[(alert_type, location_name)] = datetime.now(timezone.utc)

    def _create_alert(self, alert_type, severity, location_name, message):
        """Write one alert to the database."""
        if self._is_on_cooldown(alert_type, location_name):
            return False

        success = self.db.save_alert({
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "location_name": location_name,
            "alert_type": f"{severity}:{alert_type}",
            "message": message,
            "delivered": True,
        })

        if success:
            self._record_alert(alert_type, location_name)
            self.alert_count += 1
            emoji = {"critical": "🔴", "warning": "🟠", "info": "🟡"}.get(severity, "⚪")
            logger.warning(f"  {emoji} ALERT [{severity.upper()}] {alert_type} | {location_name} | {message}")
            return True
        return False

    def _cleanup_cooldowns(self):
        """Remove expired cooldown entries to prevent memory buildup."""
        now = datetime.now(timezone.utc)
        cutoff = timedelta(minutes=ALERT_COOLDOWN_MINUTES * 2)
        expired = [k for k, v in self.recent_alerts.items() if now - v > cutoff]
        for k in expired:
            del self.recent_alerts[k]

    def evaluate(self, features_list):
        """
        Evaluate a batch of processed messages for alert conditions.
        Called by the consumer after each round of predictions.
        """
        if not features_list:
            return

        self._cleanup_cooldowns()

        current_closures = set()
        congestion_counts = {"Free Flow": 0, "Moderate": 0, "Heavy": 0, "Severe": 0, "Closed": 0}

        for f in features_list:
            location = f.get("location_name", "Unknown")
            predicted = f.get("predicted_congestion", "")
            speed = f.get("current_speed", 0)
            ff_speed = f.get("free_flow_speed", 0)
            is_anomaly = f.get("is_anomaly", False)
            anomaly_score = f.get("anomaly_score", 0)
            reason = f.get("anomaly_reason", "")
            is_rush = f.get("is_rush_hour", 0)
            road_closure = f.get("road_closure", False)
            hour = f.get("hour", 0)

            # Count congestion levels
            if predicted in congestion_counts:
                congestion_counts[predicted] += 1

            # Track closures
            if road_closure:
                current_closures.add(location)

            #  CHECK 1: Anomaly detected 
            if is_anomaly:
                if anomaly_score < -0.05:
                    severity = "critical"
                elif anomaly_score < 0:
                    severity = "warning"
                else:
                    severity = "info"

                self._create_alert(
                    "ANOMALY", severity, location,
                    f"Anomaly detected: {reason or 'unusual pattern'}. "
                    f"Speed {speed} km/h vs {ff_speed} km/h free-flow. "
                    f"Score: {anomaly_score}"
                )

            #  CHECK 2: Severe/Heavy congestion (non-rush only) 
            if predicted == "Severe" and not is_rush:
                self._create_alert(
                    "SEVERE_CONGESTION", "critical", location,
                    f"Severe congestion outside rush hour. "
                    f"Speed {speed} km/h (free-flow {ff_speed} km/h) at hour {hour}"
                )
            elif predicted == "Severe" and is_rush:
                self._create_alert(
                    "SEVERE_CONGESTION", "warning", location,
                    f"Severe congestion during rush hour. "
                    f"Speed {speed} km/h (free-flow {ff_speed} km/h)"
                )
            elif predicted == "Heavy" and not is_rush:
                self._create_alert(
                    "HEAVY_CONGESTION", "info", location,
                    f"Heavy congestion outside rush hour. "
                    f"Speed {speed} km/h (free-flow {ff_speed} km/h) at hour {hour}"
                )

            #  CHECK 3: New road closure 
            if road_closure and location not in self.previous_closures:
                self._create_alert(
                    "ROAD_CLOSURE", "warning", location,
                    f"Road closure detected. "
                    f"Speed {speed} km/h (free-flow {ff_speed} km/h). "
                    f"TomTom reports road_closure=true"
                )

        #  CHECK 4: City-wide congestion 
        total_roads = len(features_list)
        if total_roads > 0:
            congested = congestion_counts["Moderate"] + congestion_counts["Heavy"] + \
                        congestion_counts["Severe"] + congestion_counts["Closed"]
            pct = congested / total_roads * 100

            if pct > 60:
                self._create_alert(
                    "CITY_WIDE", "critical", "Cairo (All Roads)",
                    f"{pct:.0f}% of roads showing congestion or closure. "
                    f"Moderate:{congestion_counts['Moderate']} Heavy:{congestion_counts['Heavy']} "
                    f"Severe:{congestion_counts['Severe']} Closed:{congestion_counts['Closed']}"
                )
            elif pct > 40:
                self._create_alert(
                    "CITY_WIDE", "warning", "Cairo (All Roads)",
                    f"{pct:.0f}% of roads showing congestion or closure"
                )

        # Update closure tracking for next round
        self.previous_closures = current_closures

    def get_stats(self):
        """Return alert statistics for logging."""
        return {
            "total_alerts": self.alert_count,
            "active_cooldowns": len(self.recent_alerts),
        }