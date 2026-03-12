import psycopg2
from datetime import datetime
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)
cur = conn.cursor()

# Sample data mimicking TomTom response
sample_payload = {
    "frc": "FRC1",
    "currentSpeed": 16,
    "freeFlowSpeed": 23,
    "currentTravelTime": 2126,
    "freeFlowTravelTime": 1479,
    "confidence": 0.909078,
    "roadClosure": True,
    "coordinates": {"coordinate": [{"latitude": 30.0159, "longitude": 31.2175}]},
    "@version": "4",
}

cur.execute(
    """
    INSERT INTO raw_events (
        request_time, requested_lat, requested_lon,
        frc, current_speed, free_flow_speed,
        current_travel_time, free_flow_travel_time,
        confidence, road_closure, raw_payload
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""",
    (
        datetime.now(),  # request_time
        30.0444,  # requested_lat (example)
        31.2357,  # requested_lon (example)
        sample_payload["frc"],
        sample_payload["currentSpeed"],
        sample_payload["freeFlowSpeed"],
        sample_payload["currentTravelTime"],
        sample_payload["freeFlowTravelTime"],
        sample_payload["confidence"],
        sample_payload["roadClosure"],
        json.dumps(sample_payload),
    ),
)

conn.commit()
cur.close()
conn.close()
print("Inserted test row with TomTom-like data.")
