from kafka import KafkaConsumer
import json
import os
from dotenv import load_dotenv

load_dotenv()

consumer = KafkaConsumer(
    "test-topic",
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    auto_offset_reset="earliest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)

print("Waiting for messages..")
for msg in consumer:
    print(f"Received: {msg.value}")
    break  # exit after first message
