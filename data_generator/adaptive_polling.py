

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

logger = logging.getLogger(__name__)


CAIRO_TZ = ZoneInfo("Africa/Cairo")

SCHEDULE = [
    ( 7, 10,  600, "morning rush"),    # 10 min instead of 5
    (10, 16, 1200, "midday"),          # 20 min instead of 10
    (16, 19,  600, "evening rush"),    # 10 min instead of 5
    (19, 23, 1200, "evening"),         # 20 min instead of 10
    (23, 24, 1800, "night"),           # 30 min instead of 15
    ( 0,  7, 1800, "night"),
]
# Default interval if no schedule entry matches (shouldn't happen but safe)
DEFAULT_INTERVAL = 600  # 10 minutes


def get_current_poll_interval(now=None):
    """
    Returns the poll interval in seconds based on the current Cairo time
    """
    #  Allow override via env var (for testing ) 
    override = os.getenv("POLL_INTERVAL_OVERRIDE")
    if override:
        try:
            return int(override), f"override ({override}s)"
        except ValueError:
            logger.warning(f"Invalid POLL_INTERVAL_OVERRIDE: {override} — ignoring")

    #  Get current time in Cairo 
    if now is None:
        now = datetime.now(CAIRO_TZ)
    elif now.tzinfo is None:
        # If a naive datetime was passed, assume it's Cairo local time
        now = now.replace(tzinfo=CAIRO_TZ)
    else:
        # Convert to Cairo time
        now = now.astimezone(CAIRO_TZ)

    hour = now.hour

    #  Find the matching schedule entry 
    for start_h, end_h, interval, label in SCHEDULE:
        if start_h <= hour < end_h:
            return interval, label

    # Fallback (should never reach here with the schedule above)
    return DEFAULT_INTERVAL, "default"


def describe_schedule():
    """
    Returns a human-readable summary of the polling schedule.
    Useful for logging at startup.
    """
    lines = ["Adaptive polling schedule (Cairo time):"]
    for start_h, end_h, interval, label in SCHEDULE:
        minutes = interval // 60
        lines.append(
            f"  {start_h:02d}:00 - {end_h:02d}:00  "
            f"every {minutes:2d} min  ({label})"
        )
    return "\n".join(lines)
