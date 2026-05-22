

import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class WindowAggregator:
    """
    Collects traffic messages and groups them into 5-minute windows.
    When a window closes, it computes per-location averages.
    """

    def __init__(self, window_size_minutes=5):
        self.window_minutes = window_size_minutes
        # {window_start: {location_name: [list of messages]}}
        self.windows = defaultdict(lambda: defaultdict(list))
        self.flushed_windows = set()

    def _get_window_start(self, timestamp):
        """
        Rounds a timestamp DOWN to the nearest window boundary.
        Example: if window=5min, then 14:07:23 becomes 14:05:00
        """
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        minute = (timestamp.minute // self.window_minutes) * self.window_minutes
        return timestamp.replace(minute=minute, second=0, microsecond=0)

    def add_message(self, message):
        """
        Adds one traffic message to the appropriate window.
        Returns a list of completed window aggregations (may be empty).
        """
        timestamp = message.get("request_time")
        location = message.get("location_name")

        if not timestamp or not location:
            logger.warning("Message missing request_time or location_name — skipping")
            return []

        window_start = self._get_window_start(timestamp)
        self.windows[window_start][location].append(message)

        # Check if any old windows should be flushed
        return self._flush_closed_windows(timestamp)

    def _flush_closed_windows(self, current_time):
        """
        Checks all open windows and flushes any whose end time
        is before the current message timestamp.
        """
        if isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time)

        results = []
        closed_keys = []

        for window_start, locations in self.windows.items():
            window_end = window_start + timedelta(minutes=self.window_minutes)

            if current_time >= window_end and window_start not in self.flushed_windows:
                for location_name, messages in locations.items():
                    agg = self._compute_aggregation(
                        window_start, window_end, location_name, messages
                    )
                    if agg:
                        results.append(agg)

                self.flushed_windows.add(window_start)
                closed_keys.append(window_start)

        # Clean up flushed windows from memory
        for key in closed_keys:
            del self.windows[key]

        # Keep only last hour of flushed records
        cutoff = current_time - timedelta(hours=1)
        self.flushed_windows = {w for w in self.flushed_windows if w > cutoff}

        return results

    def _compute_aggregation(self, window_start, window_end, location_name, messages):
        """
        Computes averaged metrics for one location in one time window.
        Returns a dict ready for database insertion.
        """
        if not messages:
            return None

        speeds = [m["current_speed"] for m in messages if m.get("current_speed") is not None]
        ff_speeds = [m["free_flow_speed"] for m in messages if m.get("free_flow_speed") is not None]
        closures = sum(1 for m in messages if m.get("road_closure"))

        if not speeds:
            return None

        avg_speed = sum(speeds) / len(speeds)
        avg_ff = sum(ff_speeds) / len(ff_speeds) if ff_speeds else 0
        avg_ratio = avg_speed / avg_ff if avg_ff > 0 else 0

        result = {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "location_name": location_name,
            "avg_speed": round(avg_speed, 2),
            "min_speed": round(min(speeds), 2),
            "max_speed": round(max(speeds), 2),
            "avg_free_flow_speed": round(avg_ff, 2),
            "avg_congestion_ratio": round(avg_ratio, 4),
            "reading_count": len(messages),
            "closure_count": closures,
        }

        logger.info(
            f"  Window [{window_start.strftime('%H:%M')}-{window_end.strftime('%H:%M')}] "
            f"{location_name}: avg={avg_speed:.1f}km/h ratio={avg_ratio:.3f} "
            f"n={len(messages)} closures={closures}"
        )

        return result