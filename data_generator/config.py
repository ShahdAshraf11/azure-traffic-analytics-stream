# config.py loads all settings from the .env file and makes them available as variables across the project

# a built-in Python library.It lets us talk to the operating system
# We use it here to read variables from the environment
import os

# It reads our .env file and loads everything inside it into the environment so 'os.getenv' can find them
from dotenv import load_dotenv

# Step 1: Load the .env file :

# This line actually reads the .env file
# After this line runs, all the variables in .env
# are available to us through os.getenv()
# If you don't call this, os.getenv() returns None for everything
load_dotenv()


# Step 2: Read each setting from the .env file

# os.getenv('TOMTOM_API_KEY') looks for a variable called TOMTOM_API_KEY in .env and returns its value as a string
# The second argument (after the comma) is the DEFAULT value so if this variable is not in .env  use this instead

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE_URL = os.getenv(
    "TOMTOM_BASE_URL",
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
)

# Weather API settings
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = os.getenv(
    "OPENWEATHER_BASE_URL",
    "https://api.openweathermap.org/data/2.5/weather",
)

# Cairo center coords — one weather call per round covers the whole city
CAIRO_LAT = 30.0444
CAIRO_LON  = 31.2357

# Set seconds to wait between each round of API calls
POLL_INTERVAL = int(os.getenv("TOMTOM_REFRESH_INTERVAL", 60))

# Set Number of times to retry if the API call fails
# Default is 3 tries
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# Set Number of seconds to wait before retrying after a failure
RETRY_BACKOFF = int(os.getenv("RETRY_BACKOFF_SECONDS", 5))


#3- Kafka settings

# Kafka server address
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Kafka topic name like a channel where producers send messages and consumers read them.
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "traffic-data")


# 4- database settings

# All database settings are grouped into one DB_CONFIG dictionary to easily pass to psycopg2.connect(**DB_CONFIG) which is the function that opens a database connection
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int( os.getenv("POSTGRES_PORT", 5432)),  
    "dbname": os.getenv("POSTGRES_DB", "traffic_db"),  
    "user": os.getenv("POSTGRES_USER", "traffic_user"), 
    "password": os.getenv("POSTGRES_PASSWORD", "traffic_pass"), 
}

LOCATIONS = [
    {"name": "Tahrir Square", "lat": 30.0444, "lon": 31.2357},
    {"name": "Nasr City Ring Road", "lat": 30.0626, "lon": 31.3417},
    {"name": "October Bridge", "lat": 30.0603, "lon": 31.2446},
    {"name": "El-Rawda St", "lat": 30.015822, "lon": 31.223920},
    {"name": "Maadi Corniche", "lat": 29.957459, "lon": 31.250348}, 
    {"name": "El-Gomhoreya St", "lat": 30.0499, "lon": 31.2466},
    {"name": "El-Gaish St", "lat":30.052268, "lon": 31.254252},
    {"name": "Salah Salem Road", "lat": 30.0396, "lon": 31.2657},
    {"name": "Ramses St", "lat": 30.052613, "lon": 31.237925},
    {"name": "Talaat Harb St", "lat": 30.0506, "lon": 31.2404},
    {"name": "El Haram St", "lat": 30.015433, "lon": 31.214553},
    {"name": "Nile Corniche", "lat": 30.047107, "lon": 31.231616},
    {"name": "26th of July Corridor", "lat": 30.063321, "lon": 31.167581},
    {"name": "Gamal Abd El-Nasser Rd", "lat": 30.051973, "lon": 31.216775},
    {"name": "Shobra St", "lat": 30.092088,"lon":  31.245208},
    {"name": "Abdulaziz Al Saud St", "lat": 30.023352, "lon": 31.223223},
    {"name": "Al Manial St", "lat": 30.012794,"lon":  31.224867},
    {"name": "Al Malik Al Mozafar St", "lat":30.014387,"lon": 31.223665},
    {"name": "Amro Ibn Al Aas St", "lat":30.013521,"lon": 31.229385},
    {"name": "Magra El-Eyoun St", "lat": 30.020851, "lon":  31.240715},
    {"name": "Autostorad St", "lat": 29.997227,"lon": 31.278652 },
    {"name": "El-Qobba Bridge", "lat": 30.100566,"lon":  31.305483},
    {"name": "King Faisal St", "lat": 30.004008,"lon":  31.174183}, 
    {"name": "Ring Road", "lat": 29.999456,"lon":  31.119034},
    {"name": "Ahmed Oraby St", "lat": 30.062267,"lon": 31.212831},
]

CAIRO_BBOX = "31.10,29.85,31.45,30.15"

# TomTom Incidents API
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"

# Incident icon category names (TomTom codes)
INCIDENT_CATEGORIES = {
    0: "Unknown",
    1: "Accident",
    2: "Fog",
    3: "Dangerous Conditions",
    4: "Rain",
    5: "Ice",
    6: "Jam",
    7: "Lane Closed",
    8: "Road Closed",
    9: "Road Works",
    10: "Wind",
    11: "Flooding",
    14: "Broken Down Vehicle",
}

# Delay magnitude names
DELAY_MAGNITUDE = {
    0: "Unknown",
    1: "Minor",
    2: "Moderate",
    3: "Major",
    4: "Undefined",
}