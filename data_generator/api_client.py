# ============================================================
#  api_client.py
#  This file does ONE thing only:
#  Talk to the TomTom API and return traffic data.
#
#  Think of it like a "phone call" to TomTom.
#  You give it a location (lat, lon),
#  it calls TomTom, and gives you back the traffic info
#  as a clean Python dictionary.
#
#  It knows NOTHING about Kafka or the database.
#  Its only job is the API.
# ============================================================


# --- Import the libraries we need ---------------------------

# 'requests' is a library for making HTTP requests.
# An HTTP request is how Python "visits" a website or API.
# Just like your browser visits google.com, requests lets
# our code visit api.tomtom.com to get data.
import requests

# 'time' is a built-in Python library.
# We use time.sleep() to pause for a few seconds between retries
# when an API call fails.
import time

# 'logging' is a built-in Python library.
# It's like print() but smarter — it saves messages to a file
# AND shows them in the terminal at the same time.
import logging

# 'datetime' lets us get the current date and time.
# We use it to record WHEN we fetched each piece of data.
from datetime import datetime, timezone

# Import our settings from config.py
# Instead of writing os.getenv() again here, we just import
# the variables we already set up in config.py
from config import TOMTOM_API_KEY, TOMTOM_BASE_URL, MAX_RETRIES, RETRY_BACKOFF


# --- Setup logging for this file ----------------------------

# getLogger(__name__) creates a logger just for this file.
# __name__ is automatically set to the filename ('api_client').
# This means log messages from this file will be labelled
# 'api_client' so you know where they came from.
logger = logging.getLogger(__name__)


# ============================================================
#  FUNCTION: fetch_traffic
# ============================================================
# A function is a reusable block of code.
# You define it once with 'def', and call it many times.
#
# This function:
#   - Takes a latitude and longitude as input
#   - Calls the TomTom API
#   - Returns a clean dictionary of traffic data
#   - Returns None if something goes wrong
#
# The '-> dict | None' part is just a hint telling other
# developers "this function returns either a dict or None".
# Python doesn't enforce this, it's just for readability.
# ============================================================

def fetch_traffic_data(lat, lon):

    # Build the parameters (settings) for our API request.
    # These get added to the URL as:
    # ?key=YOUR_KEY&point=30.04,31.23&unit=KMPH
    params = {
        'key'  : TOMTOM_API_KEY,    # our secret API key (from config.py)
        'point': f'{lat},{lon}',    # the location — f-string combines lat and lon
        'unit' : 'KMPH',            # we want speed in km/h, not mph
    }

    # We try MAX_RETRIES times in case the API temporarily fails.
    # range(1, MAX_RETRIES + 1) gives us [1, 2, 3] if MAX_RETRIES is 3.
    # We start from 1 (not 0) just so the log message says
    # "attempt 1" instead of "attempt 0" — more readable.
    for attempt in range(1, MAX_RETRIES + 1):

        # 'try' means: attempt the code inside.
        # If anything goes wrong, jump to 'except'.
        try:
            # This is the actual API call.
            # requests.get() sends an HTTP GET request to the URL.
            # params= adds our key/point/unit to the URL automatically.
            # timeout=10 means: if TomTom doesn't reply in 10 seconds,
            # stop waiting and raise an error.
            logger.info(f'Calling TomTom API for {lat},{lon} — attempt {attempt}')
            response = requests.get(TOMTOM_BASE_URL, params=params, timeout=10)

            # Check the HTTP status code.
            # 200 = success. 403 = bad API key. 429 = too many requests.
            # We handle each case differently:

            if response.status_code == 403:
                # 403 means our API key is wrong or expired.
                # There's no point retrying — the key won't fix itself.
                # So we log an error and return None immediately.
                logger.error('HTTP 403 — Your TOMTOM_API_KEY is wrong or expired!')
                logger.error('Check your .env file and fix the key.')
                return None   # stop here, don't retry

            if response.status_code == 429:
                # 429 means we're calling TomTom too fast.
                # We wait extra long and then retry.
                wait_time = RETRY_BACKOFF * 3   # wait 3x longer than normal
                logger.warning(f'HTTP 429 — Too many requests. Waiting {wait_time}s...')
                time.sleep(wait_time)
                continue   # 'continue' jumps to the next loop iteration (retry)

            if response.status_code != 200:
                # Any other non-200 status is unexpected.
                # Log it and retry normally.
                logger.warning(f'HTTP {response.status_code} — unexpected. Retrying...')
                time.sleep(RETRY_BACKOFF * attempt)   # wait longer each attempt
                continue

            # If we reach here, status is 200 (success!).
            # response.json() converts the JSON text response
            # into a Python dictionary we can work with.
            raw_data = response.json()

            # Now we clean and reshape the data.
            # We call our helper function below to do the actual parsing.
            clean_record = _parse_response(raw_data, lat, lon)

            # Log what we got so we can see it in the terminal
            logger.info(
                f'  Got data: speed={clean_record["current_speed"]} km/h | '
                f'free-flow={clean_record["free_flow_speed"]} km/h | '
                f'road closed={clean_record["road_closure"]}'
            )

            # Return the clean record to whoever called this function.
            # This ends the function immediately.
            return clean_record

        # --- Handle specific error types ---

        except requests.exceptions.ConnectionError:
            # This happens when there's no internet connection,
            # or the TomTom server is completely unreachable.
            logger.error(f'Connection error — check your internet. Attempt {attempt}/{MAX_RETRIES}')
            time.sleep(RETRY_BACKOFF * attempt)

        except requests.exceptions.Timeout:
            # This happens when TomTom didn't reply within 10 seconds.
            logger.warning(f'Request timed out. Attempt {attempt}/{MAX_RETRIES}')
            time.sleep(RETRY_BACKOFF * attempt)

        except Exception as e:
            # This catches ANY other unexpected error.
            # 'e' contains the error message.
            logger.error(f'Unexpected error: {e}. Attempt {attempt}/{MAX_RETRIES}')
            time.sleep(RETRY_BACKOFF * attempt)

    # If we get here, all attempts failed.
    # Log the failure and return None so the producer knows to skip this location.
    logger.error(f'All {MAX_RETRIES} attempts failed for ({lat},{lon}). Skipping this location.')
    return None


# ============================================================
#  HELPER FUNCTION: _parse_response
# ============================================================
# This function is "private" — the underscore _ at the start
# is a Python convention meaning "this is an internal helper,
# other files shouldn't call this directly."
#
# Its job: take the raw messy JSON from TomTom and return
# a clean, flat dictionary with renamed fields that match
# our database column names.
#
# TomTom uses camelCase (currentSpeed)
# Our database uses snake_case (current_speed)
# This function does the translation.
# ============================================================

def _parse_response(raw_data, lat, lon):

    # The actual traffic data is nested inside 'flowSegmentData'.
    # .get() safely retrieves a key — if it doesn't exist, returns {}
    # (empty dict) instead of crashing with a KeyError.
    flow = raw_data.get('flowSegmentData', {})

    # Build and return our clean record.
    # Each line maps a TomTom field name to our database column name.
    return {

        # When did we fetch this data?
        # datetime.now(timezone.utc) = current time in UTC timezone.
        # .isoformat() converts it to a string like "2024-01-15T14:22:01+00:00"
        # This is the format PostgreSQL TIMESTAMPTZ expects.
        'request_time': datetime.now(timezone.utc).isoformat(),

        # The GPS coordinates we asked about
        'requested_lat': lat,
        'requested_lon': lon,

        # FRC = Functional Road Class (road type)
        # FRC0 = motorway, FRC1 = major road, FRC2 = secondary, etc.
        'frc': flow.get('frc'),

        # Current speed on this road right now (km/h)
        # TomTom calls it 'currentSpeed' — we rename to 'current_speed'
        'current_speed': flow.get('currentSpeed'),

        # What the speed would be with NO traffic (km/h)
        # We use this to calculate how congested the road is.
        # congestion = current_speed / free_flow_speed
        # A ratio of 0.5 means traffic is moving at half normal speed.
        'free_flow_speed': flow.get('freeFlowSpeed'),

        # How long it currently takes to travel this road segment (seconds)
        'current_travel_time': flow.get('currentTravelTime'),

        # How long it would take with no traffic (seconds)
        'free_flow_travel_time': flow.get('freeFlowTravelTime'),

        # How reliable is this reading? (0.0 to 1.0)
        # 1.0 = very confident, 0.5 = less reliable data
        'confidence': flow.get('confidence'),

        # Is the road completely closed right now? (True or False)
        # Default is False — most roads are open most of the time.
        'road_closure': flow.get('roadClosure', False),

        # Save the ENTIRE original API response as a backup.
        # This is the raw JSON as a string. We store it in the
        # database 'raw_payload' column (JSONB type) so we never
        # lose data — even if we later change what fields we extract.
        'raw_payload': raw_data,
    }
