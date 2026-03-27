# ============================================================
#  producer.py
#  This is the MAIN file — the one you actually run.
#
#  This file is the "manager." It uses the classes from
#  db_client.py and kafka_client.py to do the real work.
#
#  HOW TO RUN:
#    python producer.py
#
#  HOW TO STOP:
#    Press Ctrl+C — it will shut down cleanly.
# ============================================================


# --- Import libraries ----------------------------------------

import time       # for time.sleep() — pausing between rounds
import logging    # for saving messages to log file + terminal
import os         # for creating the logs folder


# --- Import OUR files ----------------------------------------

# Import the classes from our helper files.
# 'from X import Y' means: go into file X, bring in the class Y.
from db_client    import DatabaseClient  # talks to PostgreSQL
from kafka_client import KafkaClient     # talks to Kafka
import api_client                        # talks to TomTom API

# Import settings from config.py
from config import LOCATIONS, POLL_INTERVAL


# ============================================================
#  SETUP LOGGING
# ============================================================
# This sets up logging for ALL files in the project.
# Every file that does logging.getLogger(__name__)
# connects to this same setup automatically.
# ============================================================

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/producer.log'),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


# ============================================================
#  MAIN FUNCTION
# ============================================================

def run():

    logger.info('=' * 55)
    logger.info('  Traffic Analytics Producer — Starting')
    logger.info(f'  Monitoring {len(LOCATIONS)} locations')
    logger.info(f'  Poll interval: {POLL_INTERVAL} seconds')
    logger.info('=' * 55)

    # --- Create our class instances -------------------------
    # This is where the classes become useful.
    # Each line below creates ONE object.
    # The object opens its connection and remembers it inside itself.

    # DatabaseClient() calls __init__ which calls _connect()
    # which opens the PostgreSQL connection and stores it in self.connection
    db_connection = DatabaseClient()

    # KafkaClient() calls __init__ which calls _connect()
    # which creates the KafkaProducer and stores it in self.producer
    kafka_producer = KafkaClient()

    # Notice: no connection objects being passed around!
    # db_connection and kafka_producer each carry their own connection internally.

    round_number = 0

    # --- The main loop --------------------------------------
    # try/except/finally structure:
    #   try     = run this code normally
    #   except  = if Ctrl+C is pressed, run this
    #   finally = ALWAYS run this no matter what (cleanup)

    try:
        while True:

            round_number += 1  # same as: round_number = round_number + 1
            logger.info(f'--- Round {round_number} ---')

            success_count = 0
            fail_count    = 0

            # Loop through every location in our LOCATIONS list
            for location in LOCATIONS:

                name = location['name']
                lat  = location['lat']
                lon  = location['lon']

                # STEP 1 — Fetch from TomTom API
                # api_client has no state so we use it as a module with functions
                # fetch_traffic() returns a dict or None if it failed
                record = api_client.fetch_traffic_data(lat, lon)

                # If the API call failed completely, skip this location
                if record is None:
                    logger.warning(f'SKIP {name} — API returned nothing')
                    fail_count += 1
                    continue   # jump to next location

                # STEP 2 — Save to PostgreSQL
                # db_connection is our DatabaseClient instance
                # save_record() uses self.connection internally — no passing needed
                saved = db_connection.save_record(record, name)

                # STEP 3 — Send to kafka_producer
                # kafka_producer is our KafkaClient instance
                # send() uses self.producer internally — no passing needed
                sent = kafka_producer.send_message(record, name)

                # Count result
                if saved or sent:
                    success_count += 1
                else:
                    fail_count += 1

                # Small pause between locations so we do not
                # hit TomTom's API too fast
                time.sleep(0.5)

            # Round summary
            logger.info(
                f'Round {round_number} done — '
                f'{success_count} ok, {fail_count} failed'
            )

            # Check if DB connection is still alive after the round.
            # is_connected() runs a quick SELECT 1 ping.
            # If it returns False, reconnect() opens a fresh connection.
            if not db_connection.is_connected():
                db_connection.reconnect()

            logger.info(f'Sleeping {POLL_INTERVAL}s...\n')
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        # This runs when you press Ctrl+C
        logger.info('Stopped by user (Ctrl+C).')

    finally:
        # This ALWAYS runs — whether stopped by Ctrl+C or a crash.
        # Close connections cleanly so no data is lost.

        # Close the PostgreSQL connection
        db_connection.close()

        # Flush remaining Kafka messages then close
        kafka_producer.close_producer()

        logger.info('Producer shut down cleanly.')


# Entry point — runs when you do: python producer.py
if __name__ == '__main__':
    run()
