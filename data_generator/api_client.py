#  This file Handles ONE thing only ->Talk to the TomTom API and return traffic data.

# for making HTTP requests.
import requests

# we use time.sleep() to pause a few seconds between retries when an API call fails.
import time

# logging is Python's built-in library like print but it saves messages to a file and shows them in the terminal at the same time.
import logging

# datetime lets us get the current date and time to record when each piece of data was fetched.
from datetime import datetime, timezone
from config import TOMTOM_API_KEY, TOMTOM_BASE_URL, MAX_RETRIES, RETRY_BACKOFF

# creates a logger for this file named 'api_client' so log messages are clearly labelled with their source.
logger = logging.getLogger(__name__)

def fetch_traffic_data(lat, lon):
    '''
    Get the Data from API

    '''
    params = {
        "key": TOMTOM_API_KEY,
        "point": f"{lat},{lon}", 
        "unit": "KMPH",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # requests.get() sends an HTTP GET request to the URL
            # timeout=10 means: if TomTom doesn't reply in 10 seconds stop waiting and raise an error
            logger.info(f"Calling TomTom API for {lat},{lon} attempt {attempt}")
            response = requests.get(TOMTOM_BASE_URL, params=params, timeout=10)

            # Check the HTTP status 
            # 200 = success, 403 = bad API key ,and 429 = too many requests 

            if response.status_code == 403:
                # 403 means our API key is wrong or expired So we log an error and return None 
                logger.error("HTTP 403 : Your TOMTOM_API_KEY is wrong or expired")
                logger.error("Check your .env file and fix the key.")
                return None  # stop here and don't retry

            if response.status_code == 429:
                # 429 means we're calling TomTom too fast
                # so We wait extra long and then retry
                wait_time = RETRY_BACKOFF * 3  # wait 3x longer than normal
                logger.warning(f"HTTP 429 : Too many requests. Waiting {wait_time}s..")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                # Any other non-200 status is unexpected.
                # Log it and retry normally.
                logger.warning(f"HTTP {response.status_code} unexpected. Retrying..")
                time.sleep(RETRY_BACKOFF * attempt)  # wait longer each attempt
                continue

            # HTTP status is 200 
            # response.json() converts the JSON text response into a dictionary
            raw_data = response.json()

            # 2- reshape the data.
            clean_record = _parse_response(raw_data, lat, lon)

            # Log what we got so we can see it in the terminal
            logger.info(
                f'  Got data: speed={clean_record["current_speed"]} km/h | '
                f'free-flow={clean_record["free_flow_speed"]} km/h | '
                f'road closed={clean_record["road_closure"]}'
            )
            return clean_record

        except requests.exceptions.ConnectionError:
            # This happens when there's no internet connection or the TomTom server is completely unreachable.
            logger.error(
                f"Connection error check your internet. Attempt {attempt}/{MAX_RETRIES}"
            )
            time.sleep(RETRY_BACKOFF * attempt)

        except requests.exceptions.Timeout:
            # This happens when TomTom didn't reply within 10 seconds.
            logger.warning(f"Request timed out. Attempt {attempt}/{MAX_RETRIES}")
            time.sleep(RETRY_BACKOFF * attempt)

        except Exception as e:
            # This catches any other unexpected error.
            # 'e' contains the error message.
            logger.error(f"Unexpected error: {e}. Attempt {attempt}/{MAX_RETRIES}")
            time.sleep(RETRY_BACKOFF * attempt)

    # If we get here this means that all attempts failed.
    # Log the failure and return None so the producer knows to skip this location.
    logger.error(
        f"All {MAX_RETRIES} attempts failed for ({lat},{lon}). Skipping this location."
    )
    return None

def _parse_response(raw_data, lat, lon):
    '''
    takes messy TomTom JSON (camelCase) and returns a
    dict with snake_case fields matching our database columns.

    '''
    flow = raw_data.get("flowSegmentData", {}) #returns {} if missing
    return {
        # datetime.now(timezone.utc) = current time in UTC timezone.
        # .isoformat() converts it to a string like "2026-01-15T14:22:01+00:00"
        # This is the format PostgreSQL TIMESTAMPTZ expects.
        "request_time": datetime.now(timezone.utc).isoformat(),
        "requested_lat": lat,
        "requested_lon": lon,
        "frc": flow.get("frc"),
        "current_speed": flow.get("currentSpeed"),
        "free_flow_speed": flow.get("freeFlowSpeed"),
        "current_travel_time": flow.get("currentTravelTime"),
        "free_flow_travel_time": flow.get("freeFlowTravelTime"),
        "confidence": flow.get("confidence"),      
        "road_closure": flow.get("roadClosure", False), # Default is False
        # Save the entire original API response as raw json in the 'raw_payload' column so we never lose data
        "raw_payload": raw_data,
    }
