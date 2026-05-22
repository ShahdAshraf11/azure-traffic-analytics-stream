#  This file Handles ONE thing only ->Talk to the TomTom API and return traffic data.

# for making HTTP requests.
import requests

# we use time.sleep() to pause a few seconds between retries when an API call fails.
import time

# logging is Python's built-in library like print but it saves messages to a file and shows them in the terminal at the same time.
import logging

# datetime lets us get the current date and time to record when each piece of data was fetched.
from datetime import datetime, timezone
from config import TOMTOM_API_KEY, TOMTOM_BASE_URL,OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL, MAX_RETRIES, RETRY_BACKOFF, CAIRO_BBOX, TOMTOM_INCIDENTS_URL, INCIDENT_CATEGORIES, DELAY_MAGNITUDE

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
            clean_record = _parse_traffic_response(raw_data, lat, lon)

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

def _parse_traffic_response(raw_data, lat, lon):
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


def fetch_weather_data(lat, lon):
    """
    Calls OpenWeatherMap once per round for Cairo
    Returns a clean parsed dict ready to insert into weather_events or None on failure
    """
    if not OPENWEATHER_API_KEY:
        logger.error("OPENWEATHER_API_KEY is missing from .env — skipping weather fetch")
        return None

    params = {
        "lat":   lat,
        "lon":   lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
 # Try up to 2 times (1 original + 1 retry)
    for attempt in range(1, 3):
        try:
            logger.info("Calling OpenWeather API for Cairo...")
            response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=10)

            if response.status_code == 401:
                logger.error("HTTP 401: Your OPENWEATHER_API_KEY is wrong or not activated yet")
                return None

            if response.status_code == 429:
                logger.warning("Weather API: rate limited (429). Waiting 5s before retry...")
                time.sleep(5)
                continue

            if response.status_code != 200:
                logger.warning(f"OpenWeather returned HTTP {response.status_code} retrying...")
                time.sleep(RETRY_BACKOFF)
                continue
            
            raw_data = response.json()

            clean_record = _parse_weather_response(raw_data)

            logger.info(
                f"  Weather: {clean_record['weather_main']} | "
                f"temp={clean_record['temperature']}°C | "
                f"rain={clean_record['rain_mm']} mm"
            )
            return clean_record

        except requests.exceptions.ConnectionError:
            logger.error(f"Weather API: connection error (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)
 
        except requests.exceptions.Timeout:
            logger.warning(f"Weather API: request timed out (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)
 
        except Exception as e:
            logger.error(f"Weather API: unexpected error: {e} (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)
    
    logger.error("Weather API: all attempts failed — skipping this round")
    return None

def _parse_weather_response(raw_data):
    """
    Takes the raw OpenWeather JSON and returns a clean
    dict with snake_case fields matching our weather_events columns
    """
    return {
        "recorded_at":   datetime.now(timezone.utc).isoformat(),
        "temperature":   raw_data["main"]["temp"],
        "feels_like":    raw_data["main"]["feels_like"],
        "humidity":      raw_data["main"]["humidity"],          # in percent
        "weather_main":  raw_data["weather"][0]["main"],        # "Rain", "Clear", "Clouds"
        "weather_desc":  raw_data["weather"][0]["description"], # "light rain"
        "wind_speed":    raw_data["wind"]["speed"],             # m/s
        "rain_mm":       raw_data.get("rain", {}).get("1h", 0.0),  # 0.0 if no rain key
        "raw_payload":   raw_data,
    }


def fetch_incidents_data():
    """
    Fetches ALL active traffic incidents in the Cairo bounding box.
    One API call per round — returns a list of parsed incident dicts.
    """
    params = {
        "key": TOMTOM_API_KEY,
        "bbox": CAIRO_BBOX,
        "fields": (
            "{incidents{type,geometry{type,coordinates},"
            "properties{id,iconCategory,magnitudeOfDelay,"
            "events{description,code},startTime,endTime,"
            "from,to,length,delay,roadNumbers}}}"
        ),
        "language": "en-US",
        "categoryFilter": "0,1,2,3,4,5,6,7,8,9,10,11,14",
        "timeValidityFilter": "present",
    }

    for attempt in range(1, 3):  # 2 attempts max
        try:
            logger.info("Calling TomTom Incidents API for Cairo bounding box...")
            response = requests.get(TOMTOM_INCIDENTS_URL, params=params, timeout=15)

            if response.status_code == 403:
                logger.error("HTTP 403: TomTom API key invalid for Incidents endpoint")
                return []

            if response.status_code == 429:
                logger.warning("Incidents API: rate limited (429). Waiting 5s...")
                time.sleep(5)
                continue

            if response.status_code != 200:
                logger.warning(f"Incidents API: HTTP {response.status_code}. Retrying...")
                time.sleep(RETRY_BACKOFF)
                continue

            raw_data = response.json()
            incidents = raw_data.get("incidents", [])

            parsed = _parse_incidents(incidents)
            logger.info(f"  Incidents: {len(parsed)} active incidents found in Cairo")
            return parsed

        except requests.exceptions.ConnectionError:
            logger.error(f"Incidents API: connection error (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)

        except requests.exceptions.Timeout:
            logger.warning(f"Incidents API: timed out (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)

        except Exception as e:
            logger.error(f"Incidents API: unexpected error: {e} (attempt {attempt}/2)")
            time.sleep(RETRY_BACKOFF)

    logger.error("Incidents API: all attempts failed — skipping this round")
    return []


def _parse_incidents(incidents_list):
    """
    Converts TomTom incident GeoJSON features into flat dicts
    for database insertion.
    """
    parsed = []
    now = datetime.now(timezone.utc).isoformat()

    for feature in incidents_list:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        # Get the center point of the incident geometry
        coords = geom.get("coordinates", [])
        if coords and len(coords) > 0:
            # For LineString, take the midpoint
            if geom.get("type") == "LineString" and len(coords) > 1:
                mid = len(coords) // 2
                lon, lat = coords[mid][0], coords[mid][1]
            else:
                # Single point or first coordinate
                first = coords[0] if isinstance(coords[0], list) else coords
                lon, lat = first[0], first[1]
        else:
            lat, lon = None, None

        # Get event descriptions
        events = props.get("events", [])
        description = "; ".join([e.get("description", "") for e in events if e.get("description")])

        icon_cat = props.get("iconCategory", 0)

        parsed.append({
            "fetched_at": now,
            "incident_id": props.get("id", ""),
            "incident_type": INCIDENT_CATEGORIES.get(icon_cat, "Unknown"),
            "icon_category": icon_cat,
            "magnitude": DELAY_MAGNITUDE.get(props.get("magnitudeOfDelay", 0), "Unknown"),
            "description": description or "No description",
            "road_from": props.get("from", ""),
            "road_to": props.get("to", ""),
            "road_numbers": ", ".join(props.get("roadNumbers", [])),
            "delay_seconds": props.get("delay", 0),
            "length_meters": props.get("length", 0),
            "lat": lat,
            "lon": lon,
            "start_time": props.get("startTime"),
            "end_time": props.get("endTime"),
            "raw_geometry": geom,
        })

    return parsed