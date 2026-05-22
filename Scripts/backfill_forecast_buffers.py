
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "data_generator"))

from config import DB_CONFIG
from common.district_mapper import get_district
from inference.forecast_inference import ForecastService, MIN_HISTORY_FOR_FULL_PREDICTION



#  LOGGING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill")


#  CONFIG

# Default: pull enough readings for the buffer plus some safety margin.
# The buffer holds 145 entries; we pull 150 so we have headroom.
DEFAULT_MAX_READINGS = 150

# Default: only pull readings from the last 48 hours.
# Older readings are unlikely to reflect current traffic patterns.
DEFAULT_HOURS_BACK = 48



def row_to_buffer_record(row):
    """
    Turn a raw_events database row into a dict with the fields the
    forecast buffer needs.
    """
    current_speed   = float(row["current_speed"] or 0)
    free_flow_speed = float(row["free_flow_speed"] or 0)

    # Compute congestion_ratio (same formula as consumer)
    if free_flow_speed > 0:
        congestion_ratio = round(current_speed / free_flow_speed, 4)
    else:
        congestion_ratio = 0.0

    return {
        "request_time":     row["request_time"],
        "location_name":    row["location_name"],
        "current_speed":    current_speed,
        "free_flow_speed":  free_flow_speed,
        "congestion_ratio": congestion_ratio,
        "road_closure":     bool(row["road_closure"]),
        # Required by some downstream lookups
        "requested_lat":    row["requested_lat"],
        "requested_lon":    row["requested_lon"],
    }


#  DATABASE QUERY

def get_locations(conn):
    """Get the list of all distinct locations that have data in raw_events."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT location_name
            FROM raw_events
            WHERE location_name IS NOT NULL
              AND request_time > NOW() - INTERVAL '7 days'
            ORDER BY location_name
        """)
        return [r[0] for r in cur.fetchall()]


def get_recent_readings(conn, location_name, max_readings, hours_back):
    """
    Get the most recent N readings for one location, ordered OLDEST first.

    We sort newest-first inside the database (efficient with index), take the
    top N, then reverse on the Python side so the buffer gets them in order.
    """
    sql = """
        WITH recent AS (
            SELECT
                request_time,
                location_name,
                current_speed,
                free_flow_speed,
                road_closure,
                requested_lat,
                requested_lon
            FROM raw_events
            WHERE location_name = %s
              AND request_time > NOW() - INTERVAL %s
              AND current_speed IS NOT NULL
              AND free_flow_speed IS NOT NULL
              AND free_flow_speed > 0
            ORDER BY request_time DESC
            LIMIT %s
        )
        SELECT *
        FROM recent
        ORDER BY request_time ASC
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (location_name, f"{hours_back} hours", max_readings))
        return cur.fetchall()


#  MAIN

def main():
    parser = argparse.ArgumentParser(
        description="Backfill forecast service buffers from PostgreSQL raw_events."
    )
    parser.add_argument(
        "--max-readings", type=int, default=DEFAULT_MAX_READINGS,
        help=f"Max readings per location (default: {DEFAULT_MAX_READINGS})"
    )
    parser.add_argument(
        "--hours-back", type=int, default=DEFAULT_HOURS_BACK,
        help=f"How far back to look in raw_events (default: {DEFAULT_HOURS_BACK} hours)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would happen but don't save buffers"
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("  Forecast Buffer Backfill — Phase C cold-start handler")
    logger.info("=" * 70)
    logger.info(f"  Settings: max-readings={args.max_readings}, hours-back={args.hours_back}")
    logger.info(f"  Buffer threshold for 'warm': {MIN_HISTORY_FOR_FULL_PREDICTION} readings")
    logger.info("=" * 70)

    #  1. Connect to PostgreSQL 
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info(f"Connected to PostgreSQL: {DB_CONFIG.get('database')}")
    except psycopg2.OperationalError as e:
        logger.error(f"Could not connect to PostgreSQL: {e}")
        sys.exit(2)

    #  2. Initialize ForecastService (loads models + previous buffers) 
    stats_path  = os.path.join(PROJECT_ROOT, "common", "location_stats.json")
    models_dir  = os.path.join(PROJECT_ROOT, "models")
    buffer_path = os.path.join(PROJECT_ROOT, "logs", "forecast_buffers.pkl")

    class _Mapper:
        @staticmethod
        def get_district(lat, lon):
            return get_district(lat, lon)

    try:
        service = ForecastService(
            models_dir=models_dir,
            stats_path=stats_path,
            district_mapper=_Mapper(),
            buffer_persist_path=buffer_path,
        )
        logger.info(f"ForecastService loaded — buffers persist to: {buffer_path}")
    except Exception as e:
        logger.error(f"Could not initialize ForecastService: {e}")
        conn.close()
        sys.exit(2)

    #  3. Find all locations with historical data 
    locations = get_locations(conn)
    if not locations:
        logger.error("No locations found in raw_events. Has the producer ever run?")
        conn.close()
        sys.exit(1)
    logger.info(f"Found {len(locations)} locations with historical data")

    #  4. Per-location backfill 
    results = {
        "warm":     [],          # locations now at >= 145 readings
        "partial":  [],          # locations with some readings but <145
        "empty":    [],          # locations with no historical data
    }
    total_pushed = 0

    for i, loc in enumerate(locations, start=1):
        readings = get_recent_readings(conn, loc, args.max_readings, args.hours_back)
        n_readings = len(readings)

        if n_readings == 0:
            results["empty"].append(loc)
            logger.warning(f"  [{i:2d}/{len(locations)}] {loc:30s} — no readings found")
            continue

        # Push each reading into the buffer in chronological order
        for row in readings:
            record = row_to_buffer_record(row)
            service.update_buffer(record)
            total_pushed += 1

        # Check if this location is now warm
        if service.is_warm(loc):
            results["warm"].append(loc)
            status = "WARM"
        else:
            results["partial"].append(loc)
            status = f"partial ({service.buffer_size(loc)}/{MIN_HISTORY_FOR_FULL_PREDICTION})"

        logger.info(f"  [{i:2d}/{len(locations)}] {loc:30s} — {n_readings:3d} pushed, {status}")

    #  5. Save the warm buffers to disk 
    if args.dry_run:
        logger.info("DRY RUN — buffers NOT saved")
    else:
        try:
            service.save_buffers()
            logger.info(f"Buffers saved to: {buffer_path}")
        except Exception as e:
            logger.error(f"Failed to save buffers: {e}")

    #  6. Print summary 
    logger.info("=" * 70)
    logger.info("  BACKFILL SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total readings pushed:  {total_pushed}")
    logger.info(f"  Warm locations:         {len(results['warm'])} / {len(locations)}")
    logger.info(f"  Partially warm:         {len(results['partial'])}")
    logger.info(f"  No data:                {len(results['empty'])}")

    if results["warm"]:
        logger.info(f"  Warm: {', '.join(results['warm'][:5])}"
                    f"{' ...' if len(results['warm']) > 5 else ''}")

    if results["partial"]:
        logger.info(f"  Partial: {', '.join(results['partial'])}")

    if results["empty"]:
        logger.info(f"  Empty: {', '.join(results['empty'])}")

    logger.info("=" * 70)
    logger.info("")
    if len(results['warm']) == len(locations):
        logger.info(" All locations warmed — forecasts will work immediately.")
    elif len(results['warm']) > 0:
        logger.info(" Some locations warmed — those will produce forecasts immediately.")
        logger.info("   Partial ones will warm up naturally as the consumer runs.")
    else:
        logger.info("  No locations fully warmed.")
        logger.info("   Try increasing --hours-back or --max-readings.")
    logger.info("")
    logger.info("Next step: restart the consumer to load these buffers and start forecasting.")

    conn.close()


if __name__ == "__main__":
    main()
