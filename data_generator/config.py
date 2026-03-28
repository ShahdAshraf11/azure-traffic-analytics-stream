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
    {"name": "Maadi Corniche", "lat": 29.9602, "lon": 31.2569},
    {"name": "El-Gomhoreya St", "lat": 30.0499, "lon": 31.2466},
    {"name": "El-Gaish St", "lat": 30.0523, "lon": 31.2542},
    {"name": "Salah Salem Road", "lat": 30.0396, "lon": 31.2657},
    {"name": "Ramses St", "lat": 30.052613, "lon": 31.237925},
    {"name": "Talaat Harb St", "lat": 30.0506, "lon": 31.2404},
    {"name": "El Haram St", "lat": 30.015433, "lon": 31.214553},
    {"name": "Nile Corniche", "lat": 30.047107, "lon": 31.231616},
    {"name": "26th of July Corridor", "lat": 30.063321, "lon": 31.167581},
    {"name": "Gamal Abd El-Nasser Rd", "lat": 30.051973, "lon": 31.216775},
]
