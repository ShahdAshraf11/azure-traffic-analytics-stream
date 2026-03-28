import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM raw_events;")
count = cur.fetchone()[0]
print(f"Number of rows in raw_events: {count}")
cur.close()
conn.close()
