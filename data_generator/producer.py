import time
import logging  
import os  

from db_client import DatabaseClient 
from kafka_client import KafkaClient  
import api_client 
from config import LOCATIONS, POLL_INTERVAL, CAIRO_LAT, CAIRO_LON
from adaptive_polling import get_current_poll_interval, describe_schedule

# setup Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR     = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE     = os.path.join(LOGS_DIR, "producer.log")
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def run():
    logger.info("=" * 55)
    logger.info("  Traffic Analytics Producer — Starting")
    logger.info(f"  Monitoring {len(LOCATIONS)} locations")
    # Show adaptive polling schedule at startup
    for line in describe_schedule().split("\n"):
        logger.info(f"  {line}")
    logger.info("=" * 55)

    # Create instances 
    db_connection = DatabaseClient()
    kafka_producer = KafkaClient()
    round_number = 0
    try:
        while True:
            round_number += 1
            logger.info(f"--- Round {round_number} ---")
            # STEP 0: Fetch weather once per round
            weather = api_client.fetch_weather_data(CAIRO_LAT, CAIRO_LON)
            if weather:
                db_connection.save_weather_record(weather)
            else:
                logger.warning("Weather data unavailable this round continuing without it")

            # STEP 0b: Fetch traffic incidents for Cairo (one call per round)
            incidents = api_client.fetch_incidents_data()
            if incidents:
                db_connection.save_incident_records(incidents)
            else:
                logger.info("No active incidents in Cairo this round")

            success_count = 0
            fail_count = 0
            for location in LOCATIONS:
                name = location["name"]
                lat = location["lat"]
                lon = location["lon"]

                # STEP 1 :Fetch from TomTom API
                record = api_client.fetch_traffic_data(lat, lon)
                # If the API call failed completely, skip this location
                if record is None:
                    logger.warning(f"SKIP {name} : API returned nothing")
                    fail_count += 1
                    continue  # jump to next location

                # STEP 2 : Save to PostgreSQL
                saved = db_connection.save_traffic_record(record, name)

                # STEP 3 : Send to kafka_producer
                # This way the consumer gets traffic + weather in one message
                # without needing a separate DB query
                if weather:
                    record["weather_temp"]  = weather["temperature"]
                    record["weather_humid"] = weather["humidity"]
                    record["weather_wind"]  = weather["wind_speed"]
                    record["weather_rain"]  = weather["rain_mm"]
                    record["weather_main"]  = weather["weather_main"]

                sent = kafka_producer.send_message(record, name)

                if saved or sent:
                    success_count += 1
                else:
                    fail_count += 1

                # Small pause between locations so we do not hit API too fast
                time.sleep(0.5)

            # Round summary
            logger.info(
                f"Round {round_number} done — "
                f"{success_count} ok, {fail_count} failed"
            )

            # Check if DB connection is still open after the round
            if not db_connection.is_connected():
                db_connection.reconnect()

            # Adaptive sleep based on time-of-day
            sleep_seconds, label = get_current_poll_interval()
            logger.info(f"Sleeping {sleep_seconds}s "
                        f"({sleep_seconds // 60} min, {label})...\n")
            time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        # This runs when you press Ctrl+C
        logger.info("Stopped by user")

    finally:
        db_connection.close()
        # Flush remaining Kafka messages then close
        kafka_producer.close_producer()

        logger.info("Producer shut down")


if __name__ == "__main__":
    run()
