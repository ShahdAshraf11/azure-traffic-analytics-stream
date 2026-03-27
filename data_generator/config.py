# ============================================================
#  config.py
#  This file does ONE thing only:
#  Read our settings from the .env file and store them
#  as variables so every other file can use them.
#
#  Think of it like a "settings page" for the whole project.
#  If you want to change any setting, you only change it HERE
#  or in the .env file — not in 4 different places.
# ============================================================


# --- Step 1: Import the libraries we need -------------------

# 'os' is a built-in Python library.
# It lets us talk to the operating system.
# We use it here to READ variables from the environment.
import os

# 'load_dotenv' comes from the 'python-dotenv' library.
# It reads our .env file and loads everything inside it
# into the environment so 'os.getenv' can find them.
from dotenv import load_dotenv


# --- Step 2: Load the .env file -----------------------------

# This line actually reads the .env file.
# After this line runs, all the variables in .env
# are available to us through os.getenv().
# If you don't call this, os.getenv() returns None for everything.
load_dotenv()


# --- Step 3: Read each setting from the .env file -----------

# os.getenv('NAME') looks for a variable called NAME in .env
# and returns its value as a string.
# The second argument (after the comma) is the DEFAULT value —
# meaning: "if this variable is not in .env, use this instead."


# Your TomTom API key — the secret key that lets us call their API.
# There is NO default here because there is no backup — you MUST
# add this to your .env file or the whole project won't work.
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')

# The TomTom API URL — the web address we send our requests to.
# This is the "door" we knock on to get traffic data.
TOMTOM_BASE_URL = os.getenv(
    'TOMTOM_BASE_URL',
    'https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json'
)

# How many seconds to wait between each round of API calls.
# Default is 60 seconds (1 minute) if not set in .env.
# We wrap it in int() because os.getenv() always returns a STRING
# like "60" — but we need a NUMBER like 60 to use in time.sleep().
POLL_INTERVAL = int(os.getenv('TOMTOM_REFRESH_INTERVAL', 60))

# How many times to retry if the API call fails.
# Default is 3 tries.
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))

# How many seconds to wait before retrying after a failure.
# Default is 5 seconds.
RETRY_BACKOFF = int(os.getenv('RETRY_BACKOFF_SECONDS', 5))


# --- Kafka settings -----------------------------------------

# The address of our Kafka server.
# Kafka is running inside Docker on our computer, so we use
# 'localhost' (meaning "this same computer") and port 9092.
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

# The name of the "channel" inside Kafka where we send messages.
# Think of a topic like a WhatsApp group — the producer sends
# messages to it, and the consumer reads from it.
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'traffic-data')


# --- PostgreSQL (database) settings -------------------------

# Instead of having 5 separate variables, we put all the
# database settings into ONE dictionary called DB_CONFIG.
# A dictionary in Python is like a table with key:value pairs.
# We will later pass this directly to psycopg2.connect(**DB_CONFIG)
# which is the function that opens a database connection.
DB_CONFIG = {
    'host'    : os.getenv('POSTGRES_HOST', 'localhost'),  # where is the DB running?
    'port'    : int(os.getenv('POSTGRES_PORT', 5432)),    # which port? (5432 is default for PostgreSQL)
    'dbname'  : os.getenv('POSTGRES_DB', 'traffic_db'),   # name of our database
    'user'    : os.getenv('POSTGRES_USER', 'traffic_user'), # username to log in
    'password': os.getenv('POSTGRES_PASSWORD', 'traffic_pass'), # password to log in
}


# --- Locations to monitor -----------------------------------

# This is a list of roads/places we want to get traffic data for.
# Each location is a dictionary with 3 things:
#   'name' : a human-readable label (for our logs)
#   'lat'  : latitude  (the vertical GPS coordinate)
#   'lon'  : longitude (the horizontal GPS coordinate)
#
# You can get lat/lon for any place by:
# 1. Going to Google Maps
# 2. Right-clicking anywhere on the map
# 3. The first number shown is lat, second is lon
LOCATIONS = [
    {'name': 'Tahrir Square',         'lat': 30.0444, 'lon': 31.2357},
    {'name': 'Nasr City Ring Road',   'lat': 30.0626, 'lon': 31.3417},
    {'name': 'October Bridge',        'lat': 30.0603, 'lon': 31.2446},
    {'name': 'El-Rawda St',           'lat': 30.015822,'lon':31.223920},
    {'name': 'Maadi Corniche',        'lat': 29.9602, 'lon': 31.2569},
    {'name': 'El-Gomhoreya St',       'lat': 30.0499, 'lon': 31.2466},
    {'name': 'El-Gaish St',           'lat': 30.0523, 'lon': 31.2542},
    {'name': 'Salah Salem Road',      'lat': 30.0396, 'lon': 31.2657},
    {'name': 'Ramses St',             'lat': 30.052613, 'lon': 31.237925},
    {'name': 'Talaat Harb St',        'lat': 30.0506, 'lon': 31.2404},
    {'name': 'El Haram St',           'lat': 30.015433, 'lon': 31.214553},
    {'name': 'Nile Corniche',         'lat': 30.047107, 'lon': 31.231616},
    {'name': '26th of July Corridor', 'lat': 30.063321, 'lon': 31.167581},
    {'name': 'Gamal Abd El-Nasser Rd','lat': 30.051973, 'lon': 31.216775},
]
