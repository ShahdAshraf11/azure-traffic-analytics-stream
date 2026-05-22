
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("data_quality")


# Cairo bounding box — coordinates are inside Cairo metropolitan area
# Used by check #5 (coordinate validation)
CAIRO_LAT_MIN, CAIRO_LAT_MAX = 29.85, 30.20    # roughly south to north
CAIRO_LON_MIN, CAIRO_LON_MAX = 31.05, 31.45    # roughly west to east

# Quality thresholds
PASS_THRESHOLD = 50          # below this, message is dropped
WARN_THRESHOLD = 80          # below this, message is flagged but kept

# Deductions per check failure
DEDUCT_FATAL    = 50         # missing fields, broken data — major issue
DEDUCT_CRITICAL = 30         # impossible values
DEDUCT_WARNING  = 15         # suspicious but possible
DEDUCT_INFO     = 5          # minor inconsistency

# Stale data threshold (10 minutes — your producer polls every ~3 min)
STALE_DATA_MINUTES = 10


class DataQualityResult:
    """Holds the result of a quality check on one message."""

    def __init__(self):
        self.score = 100             # start with perfect score
        self.issues = []             # list of issue dicts: {"check", "severity", "message"}
        self.passed = True           # False if score drops below PASS_THRESHOLD or fatal issue
        self.fatal = False           # True if message can't be processed at all

    def add_issue(self, check_name, severity, message):
        """Record an issue and deduct points based on severity."""
        deduction = {
            "fatal":    DEDUCT_FATAL,
            "critical": DEDUCT_CRITICAL,
            "warning":  DEDUCT_WARNING,
            "info":     DEDUCT_INFO,
        }.get(severity, 0)

        self.score = max(0, self.score - deduction)
        self.issues.append({
            "check": check_name,
            "severity": severity,
            "message": message,
        })

        if severity == "fatal":
            self.fatal = True
            self.passed = False
        elif self.score < PASS_THRESHOLD:
            self.passed = False

    def summary(self):
        """Brief human-readable summary."""
        if not self.issues:
            return "PASS (score=100)"
        return (f"{'PASS' if self.passed else 'FAIL'} "
                f"(score={self.score}, {len(self.issues)} issues)")


class DataQualityChecker:
    """
    Validates Kafka messages before they go to ML.
    Stateless — one instance can validate many messages safely.
    """

    def check(self, msg):
        """
        Run all 7 quality checks on a message.

        Args:
            msg: dict — the raw Kafka message

        Returns:
            DataQualityResult — has .score, .passed, .issues, .fatal
        """
        result = DataQualityResult()

        #  CHECK 1: Required fields present 
        # Without these, ML can't even run. Fatal.
        if not msg.get("location_name"):
            result.add_issue(
                "required_fields", "fatal",
                "missing location_name"
            )
        if msg.get("requested_lat") is None or msg.get("requested_lon") is None:
            result.add_issue(
                "required_fields", "fatal",
                "missing lat/lon coordinates"
            )

        # If fatal, we can stop here — message is unusable
        if result.fatal:
            return result

        #  CHECK 2: Speed sanity 
        # Speeds outside [0, 200] km/h are TomTom errors
        speed = msg.get("current_speed")
        if speed is None:
            result.add_issue("speed_sanity", "fatal", "current_speed is null")
        elif speed < 0:
            result.add_issue(
                "speed_sanity", "critical",
                f"negative speed: {speed} km/h"
            )
        elif speed > 200:
            result.add_issue(
                "speed_sanity", "critical",
                f"unrealistic speed: {speed} km/h (max expected: 200)"
            )

        #  CHECK 3: Free-flow speed sanity 
        # free_flow_speed is the reference for congestion ratio. Must be > 0.
        ff = msg.get("free_flow_speed")
        if ff is None or ff <= 0:
            result.add_issue(
                "free_flow_sanity", "critical",
                f"invalid free_flow_speed: {ff}"
            )

        #  CHECK 4: Closure-speed consistency 
        # If TomTom says road is closed BUT speed equals free-flow, the closure
        # flag is probably stale. Common with construction zones where the flag
        # stays True after the road reopens.
        if msg.get("road_closure") and speed and ff and ff > 0:
            ratio = speed / ff
            if ratio >= 0.80:  # 80%+ of free-flow speed = traffic clearly flowing
                result.add_issue(
                    "closure_consistency", "warning",
                    f"closure flag set but traffic flowing "
                    f"(speed={speed} = {ratio:.0%} of free-flow {ff})"
                )

        #  CHECK 5: Coordinates within Cairo 
        # If lat/lon are outside Cairo bounds, something is seriously wrong.
        lat = msg.get("requested_lat")
        lon = msg.get("requested_lon")
        if lat is not None and lon is not None:
            if not (CAIRO_LAT_MIN <= lat <= CAIRO_LAT_MAX):
                result.add_issue(
                    "coordinates", "critical",
                    f"latitude {lat} outside Cairo bounds "
                    f"({CAIRO_LAT_MIN}-{CAIRO_LAT_MAX})"
                )
            if not (CAIRO_LON_MIN <= lon <= CAIRO_LON_MAX):
                result.add_issue(
                    "coordinates", "critical",
                    f"longitude {lon} outside Cairo bounds "
                    f"({CAIRO_LON_MIN}-{CAIRO_LON_MAX})"
                )

        #  CHECK 6: Reading is recent (not stale) 
        # If producer is lagging, the reading might be old.
        # Stale data is OK to use but worth logging.
        ts_str = msg.get("request_time")
        if ts_str:
            try:
                ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                # Make sure ts has timezone info for comparison
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_minutes = (datetime.now(timezone.utc) - ts).total_seconds() / 60
                if age_minutes > STALE_DATA_MINUTES:
                    result.add_issue(
                        "freshness", "warning",
                        f"reading is {age_minutes:.0f} min old "
                        f"(threshold: {STALE_DATA_MINUTES} min)"
                    )
            except (ValueError, TypeError) as e:
                result.add_issue(
                    "freshness", "info",
                    f"could not parse timestamp: {ts_str}"
                )

        #  CHECK 7: Weather sanity 
        # Cairo extremes: -2°C in winter, 47°C in heat waves
        # Anything outside [-10, 60] is API glitch
        temp = msg.get("weather_temp")
        if temp is not None:
            if temp < -10 or temp > 60:
                result.add_issue(
                    "weather_sanity", "warning",
                    f"unrealistic temperature: {temp}°C"
                )

        # Humidity should be 0-100%
        humidity = msg.get("weather_humid")
        if humidity is not None and (humidity < 0 or humidity > 100):
            result.add_issue(
                "weather_sanity", "info",
                f"humidity out of range: {humidity}%"
            )

        # Rain should be non-negative
        rain = msg.get("weather_rain")
        if rain is not None and rain < 0:
            result.add_issue(
                "weather_sanity", "info",
                f"negative rain value: {rain} mm"
            )

        return result


# Stats tracker —> accumulates DQ metrics over time so we can log periodic
# summaries like "98.3% of messages passed quality checks today".
class DataQualityStats:
    """Accumulates DQ statistics for periodic reporting."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0           # passed but with issues
        self.fatal = 0              # dropped messages
        self.issue_counts = {}      # {check_name: count}

    def update(self, result):
        """Update stats from one check result."""
        self.total += 1
        if result.fatal:
            self.fatal += 1
            self.failed += 1
        elif result.passed:
            self.passed += 1
            if result.issues:
                self.warnings += 1
        else:
            self.failed += 1

        for issue in result.issues:
            check = issue["check"]
            self.issue_counts[check] = self.issue_counts.get(check, 0) + 1

    def summary(self):
        """Human-readable stats summary."""
        if self.total == 0:
            return "DQ stats: no messages yet"
        pass_rate = (self.passed / self.total) * 100
        most_common = sorted(self.issue_counts.items(),
                             key=lambda x: -x[1])[:3]
        most_common_str = ", ".join(f"{k}:{v}" for k, v in most_common) if most_common else "none"
        return (f"DQ: {self.total} checked, {pass_rate:.1f}% passed, "
                f"{self.warnings} warnings, {self.fatal} dropped. "
                f"Top issues: {most_common_str}")
